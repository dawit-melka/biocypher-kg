"""Pipeline glue for entity harmonization (used by create_knowledge_graph.py).

Work units and waves
--------------------
When any adapters-config entry sets ``aliases:``, every entry becomes one or
two work units:

- ``nodes: True, edges: False``  -> one node unit (wave 1)
- ``nodes: False, edges: True``  -> one edge unit (wave 2)
- ``nodes: True, edges: True``   -> ``<name>::nodes`` (wave 1) + ``<name>::edges`` (wave 2)

Wave 1 writes nodes only, so the alias shards (and the registry merged from
them) are complete before any source edge is written; every wave-2 edge then
passes through the edge harmonizer.
"""

import csv
import importlib
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from biocypher._logger import logger

from . import fingerprint as fp
from .aliases import AliasSelection
from .registry import RegistryReader, build_registry, read_registry_fingerprint
from .resolver import KEPT_STATUSES, REPORT_COLUMNS, EdgeEndpointHarmonizer
from .schema_info import SchemaInfo
from .shard import ALIAS_LABEL, ALIAS_OF_LABEL, AliasShard, read_shard_meta, shard_paths, strip_alias_payload

HARMONIZATION_DIRNAME = "harmonization"
UNIT_SEPARATOR = "::"
ADAPTER_NAME_KEY = "_adapter_name"


class HarmonizationError(RuntimeError):
    pass


def adapter_name_of(unit_name: str, entry: dict) -> str:
    return entry.get(ADAPTER_NAME_KEY, unit_name)


def alias_selection_for(entry: dict) -> Optional[AliasSelection]:
    return AliasSelection.from_config(entry.get("aliases"))


def validate_alias_entries(adapters_dict: dict) -> Dict[str, AliasSelection]:
    """Return {adapter: selection} for alias-enabled entries; reject invalid ones."""
    selections = {}
    for name, entry in adapters_dict.items():
        try:
            selection = alias_selection_for(entry)
        except ValueError as e:
            raise HarmonizationError(f"Adapter '{name}': {e}") from e
        if selection is None:
            continue
        if not entry.get("nodes"):
            raise HarmonizationError(
                f"Adapter '{name}' sets 'aliases' but has nodes: False; aliases are derived "
                "from emitted nodes, so 'aliases' is only valid on node entries."
            )
        adapter = entry.get("adapter") or {}
        try:
            cls = getattr(importlib.import_module(adapter["module"]), adapter["cls"])
        except (ImportError, AttributeError, KeyError) as e:
            raise HarmonizationError(f"Adapter '{name}': cannot load adapter class ({e})") from e
        if not getattr(cls, "SUPPORTS_ALIASES", False):
            raise HarmonizationError(
                f"Adapter '{name}' sets 'aliases' but {adapter['cls']} does not emit alias payloads."
            )
        selections[name] = selection
    return selections


def plan_waves(adapters_dict: dict) -> Tuple[dict, dict]:
    """Split entries into (wave 1, wave 2) work units, preserving config order."""
    wave1, wave2 = {}, {}
    for name, entry in adapters_dict.items():
        nodes, edges = bool(entry.get("nodes")), bool(entry.get("edges"))
        if nodes and edges:
            wave1[f"{name}{UNIT_SEPARATOR}nodes"] = {**entry, "edges": False, ADAPTER_NAME_KEY: name}
            wave2[f"{name}{UNIT_SEPARATOR}edges"] = {**entry, "nodes": False, ADAPTER_NAME_KEY: name}
        elif edges:
            wave2[name] = entry
        else:
            wave1[name] = entry
    return wave1, wave2


def adapters_with_pending_units(adapters_dict: dict, completed_units) -> dict:
    """Entries with at least one work unit not yet completed (for pre-flight checks)."""
    completed = set(completed_units)
    pending = {}
    for name, entry in adapters_dict.items():
        split_units = {f"{name}{UNIT_SEPARATOR}nodes", f"{name}{UNIT_SEPARATOR}edges"}
        if name in completed or split_units <= completed:
            continue
        pending[name] = entry
    return pending


def _fingerprint_deps(entry: dict) -> dict:
    adapter = entry.get("adapter") or {}
    try:
        cls = getattr(importlib.import_module(adapter["module"]), adapter["cls"])
    except (ImportError, AttributeError, KeyError):
        return {}
    hook = getattr(cls, "alias_fingerprint_deps", None)
    return hook(fp.adapter_args(entry)) if hook else {}


def compute_fingerprint(name: str, entry: dict, selection: AliasSelection, schema_info: SchemaInfo, labels) -> dict:
    return fp.adapter_fingerprint(name, entry, selection, schema_info, labels, deps=_fingerprint_deps(entry))


class HarmonizationContext:
    """Per-run harmonization settings and results.

    Picklable so it can be sent to workers; the accumulated results stay in the
    main process (they are dropped when pickled).
    """

    _RUN_STATE = ("alias_results", "edge_results", "registry_stats", "executed_alias_adapters")

    def __init__(self, output_dir, schema_info: SchemaInfo, selections: Dict[str, AliasSelection],
                 all_alias_entries: Dict[str, dict], harmonize_edges: bool = True):
        self.output_dir = str(output_dir)
        self.schema_info = schema_info
        self.selections = selections
        self.all_alias_entries = all_alias_entries
        self.harmonize_edges = harmonize_edges
        self.registry_path: Optional[str] = None
        self._reset_run_state()

    def _reset_run_state(self):
        self.alias_results: Dict[str, dict] = {}
        self.edge_results: Dict[str, dict] = {}
        self.registry_stats: Optional[dict] = None
        self.executed_alias_adapters = set()

    def __getstate__(self):
        return {k: v for k, v in self.__dict__.items() if k not in self._RUN_STATE}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._reset_run_state()

    # ── run state (main process) ───────────────────────────────────────────

    def record(self, unit_result: dict):
        alias = unit_result.get("alias")
        if alias:
            self.alias_results[alias["adapter"]] = alias
            self.executed_alias_adapters.add(alias["adapter"])
        edges = unit_result.get("harmonization")
        if edges:
            self.edge_results[edges["adapter"]] = edges

    def checkpoint_state(self) -> dict:
        return {"aliases": self.alias_results, "edges": self.edge_results, "registry": self.registry_stats}

    def restore(self, extra: Optional[dict]):
        state = (extra or {}).get("harmonization") or {}
        self.alias_results = dict(state.get("aliases") or {})
        self.edge_results = dict(state.get("edges") or {})
        self.registry_stats = state.get("registry")

    def barrier(self, wave2_units, completed_units):
        """Between waves: verify shards and build the registry wave 2 resolves against."""
        if not self.harmonize_edges:
            logger.info("Edge harmonization disabled (--no-harmonize-edges); not building the alias registry.")
            return
        resumed = set(self.selections) - self.executed_alias_adapters
        previous = (self.registry_stats or {}).get("fingerprint")
        stats = self.build_registry(self.executed_alias_adapters, resumed)
        completed = set(completed_units)
        if previous and previous != stats["fingerprint"] and any(unit in completed for unit in wave2_units):
            raise HarmonizationError(
                "The alias registry differs from the one used by edge adapters completed in the "
                "checkpointed run, so their edges were resolved differently. Re-run with --restart."
            )
        self.registry_stats = stats

    def summary(self) -> dict:
        return summarize(self.alias_results, self.edge_results, self.registry_stats,
                         self.write_merged_reports(), self.harmonize_edges)

    # ── paths ──────────────────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return Path(self.output_dir) / HARMONIZATION_DIRNAME

    @property
    def shard_dir(self) -> Path:
        return self.root / "shards"

    @property
    def edge_report_dir(self) -> Path:
        return self.root / "edges"

    @property
    def registry_file(self) -> Path:
        return self.root / "registry.db"

    # ── wave 1: alias shards ───────────────────────────────────────────────

    def open_shard(self, adapter_name: str, adapter) -> Optional[AliasShard]:
        selection = self.selections.get(adapter_name)
        if selection is None:
            return None
        if not getattr(adapter, "SUPPORTS_ALIASES", False):
            raise HarmonizationError(
                f"Adapter '{adapter_name}' ({type(adapter).__name__}) sets 'aliases' "
                "but does not support alias emission."
            )
        adapter.enable_aliases(selection)
        return AliasShard(
            self.shard_dir, adapter_name, selection, self.schema_info,
            default_scope=getattr(adapter, "taxon_id", None),
        )

    @staticmethod
    def wrap_nodes(nodes, shard: AliasShard, adapter):
        legacy = tuple(getattr(adapter, "ALIAS_LEGACY_PROPS", ()))
        for node_id, label, props in nodes:
            props, payload = strip_alias_payload(props, legacy)
            shard.record_node(node_id, label, props, payload)
            yield node_id, label, props

    def write_alias_outputs(self, writer, shard: AliasShard, adapter_name: str, entry: dict, adapter) -> dict:
        """Write alias nodes and alias_of edges, finalize the shard, return counts.

        Counts come from the shard, not from the writer: writers disagree on
        whether their returned counters are per call or cumulative.
        """
        prefix = f"{entry['outdir']}/aliases/{adapter_name}"
        add_provenance = getattr(adapter, "add_provenance", False)
        source = getattr(adapter, "source", None) if add_provenance else None
        source_url = getattr(adapter, "source_url", None) if add_provenance else None
        writer.write_nodes(shard.iter_alias_nodes(), path_prefix=prefix)
        writer.write_edges(shard.iter_alias_of_edges(source, source_url), path_prefix=prefix)

        summary = shard.summary()
        edge_counts = {
            f"{ALIAS_OF_LABEL}|{ALIAS_LABEL}|{label}": count
            for label, count in shard.alias_of_counts_by_label().items()
        }
        props = shard.alias_node_prop_keys()
        edge_props = {"alias_type", "alias_source"} | ({"source", "source_url"} if add_provenance else set())

        selection = self.selections[adapter_name]
        fingerprint = compute_fingerprint(adapter_name, entry, selection, self.schema_info, sorted(shard.labels))
        shard.finalize(fingerprint)
        return {
            "adapter": adapter_name,
            "summary": summary,
            "node_counts": {ALIAS_LABEL: summary["alias_nodes"]} if summary["alias_nodes"] else {},
            "node_props": {ALIAS_LABEL: sorted(props)} if props else {},
            "edge_counts": edge_counts,
            "edge_props": sorted(edge_props),
        }

    # ── barrier ────────────────────────────────────────────────────────────

    def verify_shards(self, executed_now, resumed) -> Tuple[Dict[str, Path], List[str]]:
        """Check alias shards before they are merged into the registry.

        - adapters executed in this run: their shard must exist (it was just written);
        - adapters completed in an earlier run and resumed from the checkpoint:
          the shard must exist and match the current config, else fail (--restart);
        - adapters outside this run: a stale shard fails the run, a missing one
          only warns (fewer resolutions, never a wrong rewrite).

        Returns (usable shards, adapters with no shard).
        """
        executed_now, resumed = set(executed_now), set(resumed)
        usable, missing, stale = {}, [], {}
        for name, entry in sorted(self.all_alias_entries.items()):
            path, _ = shard_paths(self.shard_dir, name)
            meta = read_shard_meta(path)
            if meta is None:
                missing.append(name)
                continue
            if name not in executed_now:
                selection = alias_selection_for(entry)
                expected = compute_fingerprint(name, entry, selection, self.schema_info, meta["labels"])
                if fp.digest(expected) != fp.digest(meta["fingerprint"]):
                    stale[name] = fp.diff(meta["fingerprint"], expected)
                    continue
            usable[name] = path

        broken = sorted((set(missing) | set(stale)) & (executed_now | resumed))
        if broken:
            details = "; ".join(
                f"{name} ({'no finished shard' if name in missing else 'changed: ' + ', '.join(stale[name])})"
                for name in broken
            )
            raise HarmonizationError(
                f"Alias shard missing or out of date for adapter(s) in this run: {details}. "
                "Re-run with --restart."
            )
        if stale:
            details = "; ".join(f"{name} (changed: {', '.join(fields)})" for name, fields in sorted(stale.items()))
            raise HarmonizationError(
                f"Stale alias shard(s) from an earlier run: {details}. Include these adapters in this run "
                "so their shards are rebuilt, or pass --no-harmonize-edges."
            )
        for name in missing:
            logger.warning(
                f"No alias shard for '{name}' (not run in this build); edge endpoints that "
                "reference its entities cannot be resolved."
            )
        return usable, missing

    def build_registry(self, executed_now, resumed) -> dict:
        shards, missing = self.verify_shards(executed_now, resumed)
        stats = build_registry(shards, self.registry_file)
        stats["registry_complete"] = not missing
        stats["missing_shards"] = sorted(missing)
        self.registry_path = str(self.registry_file)
        return stats

    def registry_fingerprint(self) -> Optional[str]:
        return read_registry_fingerprint(self.registry_file)

    # ── wave 2: edges ──────────────────────────────────────────────────────

    def edge_harmonizer(self, adapter_name: str) -> Optional[EdgeEndpointHarmonizer]:
        if not self.harmonize_edges or not self.registry_path:
            return None
        return EdgeEndpointHarmonizer(RegistryReader(self.registry_path), self.schema_info, adapter_name)

    def close_harmonizer(self, adapter_name: str, harmonizer: EdgeEndpointHarmonizer) -> dict:
        report = harmonizer.write_report(self.edge_report_dir / f"{adapter_name}.tsv")
        summary = harmonizer.summary()
        summary["adapter"] = adapter_name
        summary["report"] = str(report) if report else None
        return summary

    # ── end of run ─────────────────────────────────────────────────────────

    def write_merged_reports(self) -> Dict[str, str]:
        """Merge per-adapter TSVs into unresolved_ids.tsv and ambiguous_ids.tsv."""
        rows = {status: [] for status in KEPT_STATUSES}
        if self.edge_report_dir.exists():
            for path in sorted(self.edge_report_dir.glob("*.tsv")):
                with open(path, newline="") as f:
                    for row in csv.DictReader(f, delimiter="\t"):
                        if row["status"] in rows:
                            rows[row["status"]].append(row)
        outputs = {}
        for status, file_name in (("unresolved", "unresolved_ids.tsv"), ("ambiguous", "ambiguous_ids.tsv"),
                                  ("type_mismatch", "type_mismatch_ids.tsv")):
            path = self.root / file_name
            selected = sorted(rows[status], key=lambda r: (-int(r["count"]), r["adapter"], r["raw_id"]))
            if not selected:
                if path.exists():
                    path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(selected)
            outputs[status] = str(path)
        return outputs


def summarize(alias_results: Dict[str, dict], edge_results: Dict[str, dict], registry_stats: Optional[dict],
              reports: Dict[str, str], harmonize_edges: bool) -> dict:
    """The ``harmonization`` section of graph_info.json."""
    alias_nodes = Counter()
    alias_edges = Counter()
    by_alias_type = Counter()
    for result in alias_results.values():
        alias_nodes.update(result.get("node_counts", {}))
        for key, count in result.get("edge_counts", {}).items():
            alias_edges[key.split("|")[-1]] += count
        by_alias_type.update(result.get("summary", {}).get("links_by_alias_type", {}))

    statuses = Counter()
    for result in edge_results.values():
        statuses.update(result.get("statuses", {}))

    return {
        "alias_enabled_adapters": sorted(alias_results),
        "alias_nodes": sum(alias_nodes.values()),
        "alias_of_edges": sum(alias_edges.values()),
        "alias_of_edges_by_target": dict(sorted(alias_edges.items())),
        "alias_links_by_type": dict(sorted(by_alias_type.items())),
        "edge_harmonization": {
            "enabled": harmonize_edges,
            "statuses": dict(sorted(statuses.items())),
            "by_adapter": {name: result.get("statuses", {}) for name, result in sorted(edge_results.items())},
        },
        "registry": registry_stats or {},
        "reports": reports,
    }
