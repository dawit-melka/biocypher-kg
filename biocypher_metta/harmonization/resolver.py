"""Edge-endpoint harmonization against the alias registry.

Each endpoint whose node type has canonical nodes in the registry is looked up
by its normalized key:

- ``unchanged``      the endpoint already is the emitted canonical ID
- ``normalized``     same identifier, different spelling (prefix case, version,
                     ``UniProtKB:`` vs bare accession): rewritten to the emitted ID
- ``resolved``       an identifier alias with exactly one canonical entity at its
                     best tier: rewritten to that entity's emitted ID
- ``ambiguous``      several canonical entities claim the key: kept as-is
- ``type_mismatch``  only entities of a type the edge does not allow: kept as-is
- ``unresolved``     no canonical entity or alias: kept as-is
- ``unmanaged``      the endpoint's node type is not harmonized in this run
- ``skipped``        the edge is an identifier link (``has xref`` and its
                     subtypes, ``alias_of``) and is left untouched

Free-text name aliases are never used to rewrite edges.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Optional

from . import curie
from .registry import RegistryReader
from .schema_info import SchemaInfo, norm_label

KEPT_STATUSES = ("ambiguous", "type_mismatch", "unresolved")
REWRITTEN_STATUSES = ("normalized", "resolved")
REPORT_COLUMNS = ("adapter", "label", "role", "node_type", "raw_id", "normalized_key", "status", "candidates", "count")


class EdgeEndpointHarmonizer:
    def __init__(self, registry: RegistryReader, schema_info: SchemaInfo, adapter_name: str,
                 max_report_rows: int = 20000):
        self.registry = registry
        self.schema_info = schema_info
        self.adapter_name = adapter_name
        self.max_report_rows = max_report_rows
        self.status_counts = Counter()
        self.label_status_counts: Dict[str, Counter] = defaultdict(Counter)
        self._report = Counter()
        self._report_overflow = 0
        self._managed = registry.managed_node_types()
        self._allowed_cache = {}
        self._class_cache = {}
        self._classify_cache = {}

    # ── public ─────────────────────────────────────────────────────────────

    def wrap(self, edges):
        skip = self.schema_info.identifier_link_labels
        for source, target, label, props in edges:
            if norm_label(label) in skip:
                self._count(label, "skipped", 2)
                yield source, target, label, props
                continue
            yield (
                self._harmonize(source, label, "source"),
                self._harmonize(target, label, "target"),
                label,
                props,
            )

    def summary(self) -> dict:
        return {
            "statuses": dict(sorted(self.status_counts.items())),
            "by_label": {label: dict(sorted(c.items())) for label, c in sorted(self.label_status_counts.items())},
            "report_rows": len(self._report),
            "report_rows_dropped": self._report_overflow,
        }

    def write_report(self, path) -> Optional[Path]:
        """Write the per-adapter TSV of rewritten and kept endpoints (None if empty).

        An empty report removes a TSV left by an earlier run of the same adapter.
        """
        path = Path(path)
        if not self._report:
            if path.exists():
                path.unlink()
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(self._report.items(), key=lambda kv: (kv[0][5], -kv[1], kv[0]))
        with open(path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerow(REPORT_COLUMNS)
            for key, count in rows:
                writer.writerow((self.adapter_name,) + key + (count,))
        return path

    # ── internals ──────────────────────────────────────────────────────────

    def _allowed(self, endpoint, label: str, role: str):
        node_type = endpoint[0] if isinstance(endpoint, tuple) else None
        cache_key = (node_type, label, role)
        allowed = self._allowed_cache.get(cache_key)
        if allowed is None:
            if node_type is not None:
                types = self.schema_info.concrete_labels(node_type)
            else:
                types = self.schema_info.endpoint_types(label, role)
            types = frozenset(t for t in types if t in self._managed)
            classes = frozenset(c for c in (self._entity_class(t) for t in types) if c)
            allowed = (types, classes)
            self._allowed_cache[cache_key] = allowed
        return allowed

    def _entity_class(self, node_type: str):
        if node_type not in self._class_cache:
            self._class_cache[node_type] = self.schema_info.entity_class(node_type)
        return self._class_cache[node_type]

    def _harmonize(self, endpoint, label: str, role: str):
        types, classes = self._allowed(endpoint, label, role)
        raw_id = endpoint[1] if isinstance(endpoint, tuple) else endpoint
        if not types or raw_id is None:
            self._count(label, "unmanaged")
            return endpoint

        memo_key = (str(raw_id), types)
        result = self._classify_cache.get(memo_key)
        if result is None:
            result = self._classify(str(raw_id), types, classes)
            if len(self._classify_cache) >= 100_000:
                self._classify_cache.clear()
            self._classify_cache[memo_key] = result
        status, new_id, key, candidates = result
        self._count(label, status)
        if status != "unchanged":
            declared = endpoint[0] if isinstance(endpoint, tuple) else "|".join(sorted(types))
            self._record(label, role, declared, raw_id, key, status, candidates)
        if new_id is None or new_id == raw_id:
            return endpoint
        return (endpoint[0], new_id) if isinstance(endpoint, tuple) else new_id

    def _classify(self, raw_id: str, types, classes):
        canonical_hits, alias_hits, keys = [], [], []
        for entity_class in sorted(classes):
            key = curie.lookup_key(raw_id, entity_class) or raw_id.upper()
            keys.append(key)
            canonical, aliases = self.registry.lookup(entity_class, key)
            canonical_hits.extend(canonical)
            alias_hits.extend(aliases)
        key = keys[0] if len(set(keys)) == 1 else "|".join(sorted(set(keys)))

        if canonical_hits:
            allowed = sorted({(t, i) for t, i in canonical_hits if t in types})
            if not allowed:
                return "type_mismatch", None, key, _fmt(canonical_hits)
            if len({i for _, i in allowed}) > 1:
                return "ambiguous", None, key, _fmt(allowed)
            emitted = allowed[0][1]
            return ("unchanged" if emitted == raw_id else "normalized"), emitted, key, emitted

        if alias_hits:
            allowed = [(tier, t, i) for tier, t, i in alias_hits if t in types]
            if not allowed:
                return "type_mismatch", None, key, _fmt((t, i) for _, t, i in alias_hits)
            best = min(tier for tier, _, _ in allowed)
            targets = sorted({(t, i) for tier, t, i in allowed if tier == best})
            if len({i for _, i in targets}) > 1:
                return "ambiguous", None, key, _fmt(targets)
            return "resolved", targets[0][1], key, targets[0][1]

        return "unresolved", None, key, ""

    def _count(self, label: str, status: str, n: int = 1):
        self.status_counts[status] += n
        self.label_status_counts[norm_label(label)][status] += n

    def _record(self, label, role, node_type, raw_id, key, status, candidates):
        row = (label, role, node_type, str(raw_id), key, status, candidates)
        if row in self._report or len(self._report) < self.max_report_rows:
            self._report[row] += 1
        else:
            self._report_overflow += 1


def _fmt(hits) -> str:
    return ";".join(f"{t}:{i}" for t, i in sorted(set(hits)))
