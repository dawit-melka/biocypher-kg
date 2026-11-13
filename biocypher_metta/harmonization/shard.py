"""Per-adapter alias shard: an on-disk SQLite record of one adapter's canonical
nodes and the aliases attached to them.

The shard is filled while the adapter's nodes stream through the writer, then
read back to emit ``alias`` nodes and ``alias_of`` edges, and finally merged
into the run's registry. Writing to ``<name>.db.tmp`` and renaming on
``finalize`` means a crashed run never leaves a shard that looks complete.
"""

import json
import os
import sqlite3
from collections import Counter
from itertools import groupby
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from biocypher._logger import logger

from . import curie
from .aliases import (
    ALIAS_PAYLOAD_KEY,
    IDENTIFIER,
    NAME,
    AliasRef,
    AliasSelection,
    alias_id,
    alias_kind,
    normalize_name,
    resolution_tier,
)
from .schema_info import SchemaInfo, norm_label

ALIAS_LABEL = "alias"
ALIAS_OF_LABEL = "alias_of"

_SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE canonical (
    entity_class TEXT NOT NULL,
    norm_key     TEXT NOT NULL,
    node_type    TEXT NOT NULL,
    node_label   TEXT NOT NULL,
    emitted_id   TEXT NOT NULL,
    PRIMARY KEY (node_type, emitted_id)
);
CREATE TABLE alias (
    alias_id        TEXT PRIMARY KEY,
    entity_class    TEXT NOT NULL,
    scope           TEXT NOT NULL,
    kind            TEXT NOT NULL,
    ident           TEXT NOT NULL,
    namespace       TEXT,
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    norm_key        TEXT NOT NULL,
    UNIQUE (entity_class, scope, kind, ident)
);
CREATE TABLE link (
    alias_id   TEXT NOT NULL,
    node_type  TEXT NOT NULL,
    node_label TEXT NOT NULL,
    emitted_id TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    tier       INTEGER,
    PRIMARY KEY (alias_id, node_type, emitted_id, alias_type, source)
);
"""

# A different identity hashing to an existing alias_id violates the PRIMARY KEY,
# which the upsert below does not cover, so collisions raise instead of merging.
_INSERT_ALIAS = """
INSERT INTO alias (alias_id, entity_class, scope, kind, ident, namespace, name, normalized_name, norm_key)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (entity_class, scope, kind, ident) DO NOTHING
"""


class AliasCollisionError(RuntimeError):
    pass


def shard_paths(shard_dir: Path, adapter_name: str):
    final = Path(shard_dir) / f"{adapter_name}.db"
    return final, final.with_name(final.name + ".tmp")


class AliasShard:
    """Write side of one adapter's shard."""

    def __init__(self, shard_dir, adapter_name: str, selection: AliasSelection,
                 schema_info: SchemaInfo, default_scope=None, batch_size: int = 10000):
        self.adapter_name = adapter_name
        self.selection = selection
        self.schema_info = schema_info
        self.default_scope = default_scope
        self.batch_size = batch_size
        self.path, self.tmp_path = shard_paths(shard_dir, adapter_name)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for stale in (self.tmp_path, self.path):
            if stale.exists():
                stale.unlink()
        self._conn = sqlite3.connect(str(self.tmp_path))
        self._conn.execute("PRAGMA journal_mode=OFF")
        self._conn.execute("PRAGMA synchronous=OFF")
        self._conn.executescript(_SCHEMA)
        self._canonical: List[tuple] = []
        self._aliases: List[tuple] = []
        self._links: List[tuple] = []
        self._class_cache: Dict[str, Optional[str]] = {}
        self.labels = set()
        self.stats = Counter()

    # ── recording ──────────────────────────────────────────────────────────

    def _entity_class(self, label: str) -> Optional[str]:
        if label not in self._class_cache:
            self._class_cache[label] = self.schema_info.entity_class(label)
        return self._class_cache[label]

    def _scope(self, entity_class: str, canonical: Optional[curie.Curie], props: dict) -> str:
        if entity_class == "ontology_term":
            return canonical.prefix.upper() if canonical else ""
        taxon = (props or {}).get("taxon_id", self.default_scope)
        return str(taxon) if taxon is not None else ""

    def record_node(self, node_id: str, label: str, props: dict, payload: Optional[List[AliasRef]]):
        entity_class = self._entity_class(label)
        if entity_class is None:
            if payload:
                self.stats["payload_on_unsupported_label"] += 1
            return

        node_type = norm_label(label)
        self.labels.add(label)
        canonical = curie.normalize(node_id, entity_class)
        canonical_key = curie.lookup_key(canonical) if canonical else str(node_id).upper()
        self._canonical.append((entity_class, canonical_key, node_type, label, node_id))
        self.stats["canonical_nodes"] += 1

        scope = self._scope(entity_class, canonical, props)
        for ref in payload or ():
            if not self.selection.allows(ref.alias_type):
                continue
            self._add_alias(entity_class, scope, canonical_key, node_type, label, node_id, ref)

        if len(self._canonical) >= self.batch_size or len(self._links) >= self.batch_size:
            self._flush()

    def _add_alias(self, entity_class, scope, canonical_key, node_type, label, node_id, ref: AliasRef):
        kind = alias_kind(ref.alias_type)
        if kind == IDENTIFIER:
            raw = ref.value if ":" in ref.value or not ref.namespace else f"{ref.namespace}:{ref.value}"
            parsed = curie.normalize(raw, entity_class)
            if parsed is None:
                kind = NAME
            else:
                key = curie.lookup_key(parsed)
                if key == canonical_key:
                    return  # same identifier as the node itself
                # identity and registry key: the case-insensitive CURIE
                ident, norm_key = key, key
                namespace, name = parsed.prefix, parsed.local
                normalized_name = parsed.local.casefold()
        if kind == NAME:
            ident = normalize_name(ref.value)
            if not ident:
                return
            namespace, name = ref.namespace, ident
            normalized_name = norm_key = ident.casefold()

        aid = alias_id(entity_class, scope, kind, ident)
        self._aliases.append((aid, entity_class, scope, kind, ident, namespace, name, normalized_name, norm_key))
        tier = resolution_tier(ref.alias_type) if kind == IDENTIFIER else None
        self._links.append((aid, node_type, label, node_id, ref.alias_type, ref.source or "", tier))
        self.stats[f"alias_type:{ref.alias_type}"] += 1

    def _flush(self):
        try:
            if self._canonical:
                self._conn.executemany("INSERT OR IGNORE INTO canonical VALUES (?, ?, ?, ?, ?)", self._canonical)
            if self._aliases:
                self._conn.executemany(_INSERT_ALIAS, self._aliases)
            if self._links:
                self._conn.executemany("INSERT OR IGNORE INTO link VALUES (?, ?, ?, ?, ?, ?, ?)", self._links)
        except sqlite3.IntegrityError as e:
            raise AliasCollisionError(
                f"{self.adapter_name}: alias ID collision while writing {self.tmp_path}: {e}"
            ) from e
        self._conn.commit()
        self._canonical, self._aliases, self._links = [], [], []

    # ── emitting ───────────────────────────────────────────────────────────

    def iter_alias_nodes(self) -> Iterator[tuple]:
        self._flush()
        rows = self._conn.execute(
            "SELECT alias_id, entity_class, scope, kind, namespace, name, normalized_name "
            "FROM alias ORDER BY alias_id"
        )
        for aid, entity_class, scope, kind, namespace, name, normalized_name in rows:
            props = {
                "name": name,
                "normalized_name": normalized_name,
                "alias_kind": kind,
                "entity_type": entity_class,
                "scope": scope,
            }
            if namespace:
                props["namespace"] = namespace
            yield aid, ALIAS_LABEL, props

    def iter_alias_of_edges(self, source: Optional[str] = None, source_url: Optional[str] = None) -> Iterator[tuple]:
        self._flush()
        rows = self._conn.execute(
            "SELECT alias_id, node_label, emitted_id, alias_type, source FROM link "
            "ORDER BY alias_id, node_label, emitted_id, alias_type, source"
        )
        for (aid, label, node_id), group in groupby(rows, key=lambda r: (r[0], r[1], r[2])):
            group = list(group)
            props = {
                "alias_type": sorted({r[3] for r in group}),
                "alias_source": sorted({r[4] for r in group if r[4]}),
            }
            if not props["alias_source"]:
                del props["alias_source"]
            if source:
                props["source"] = source
            if source_url:
                props["source_url"] = source_url
            yield (ALIAS_LABEL, aid), (label, node_id), ALIAS_OF_LABEL, props

    def alias_of_counts_by_label(self) -> Dict[str, int]:
        self._flush()
        return dict(self._conn.execute(
            "SELECT node_label, COUNT(*) FROM (SELECT DISTINCT alias_id, node_label, emitted_id FROM link) "
            "GROUP BY node_label ORDER BY node_label"
        ).fetchall())

    def alias_node_prop_keys(self) -> set:
        self._flush()
        if not self._conn.execute("SELECT 1 FROM alias LIMIT 1").fetchone():
            return set()
        keys = {"name", "normalized_name", "alias_kind", "entity_type", "scope"}
        if self._conn.execute("SELECT 1 FROM alias WHERE namespace IS NOT NULL AND namespace != '' LIMIT 1").fetchone():
            keys.add("namespace")
        return keys

    # ── completion ─────────────────────────────────────────────────────────

    def summary(self) -> dict:
        self._flush()
        alias_nodes = self._conn.execute("SELECT COUNT(*) FROM alias").fetchone()[0]
        alias_edges = self._conn.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT alias_id, node_type, emitted_id FROM link)"
        ).fetchone()[0]
        by_type = dict(self._conn.execute(
            "SELECT alias_type, COUNT(*) FROM link GROUP BY alias_type ORDER BY alias_type"
        ).fetchall())
        canonical = self._conn.execute("SELECT COUNT(*) FROM canonical").fetchone()[0]
        return {
            "canonical_nodes": canonical,
            "alias_nodes": alias_nodes,
            "alias_of_edges": alias_edges,
            "links_by_alias_type": by_type,
        }

    def finalize(self, fingerprint: dict) -> Path:
        self._flush()
        self._conn.executescript(
            "CREATE INDEX idx_canonical_key ON canonical (entity_class, norm_key);"
            "CREATE INDEX idx_link_alias ON link (alias_id);"
        )
        meta = {
            "adapter": self.adapter_name,
            "fingerprint": json.dumps(fingerprint, sort_keys=True),
            "labels": json.dumps(sorted(self.labels)),
            "summary": json.dumps(self.summary(), sort_keys=True),
        }
        self._conn.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)", meta.items())
        self._conn.commit()
        self._conn.close()
        os.replace(self.tmp_path, self.path)
        logger.info(f"{self.adapter_name}: alias shard written to {self.path}")
        return self.path

    def abort(self):
        """Discard an unfinished shard (no-op after finalize)."""
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
        if self.tmp_path.exists():
            self.tmp_path.unlink()


def read_shard_meta(path) -> Optional[dict]:
    """Meta of a finished shard, or None if it is missing or unreadable."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return {
        "adapter": meta.get("adapter"),
        "fingerprint": json.loads(meta.get("fingerprint") or "{}"),
        "labels": json.loads(meta.get("labels") or "[]"),
        "summary": json.loads(meta.get("summary") or "{}"),
    }


def strip_alias_payload(props: dict, legacy_props):
    """Split a node's props into (props without payload/legacy alias props, payload)."""
    if not props:
        return props, None
    if ALIAS_PAYLOAD_KEY not in props and not any(key in props for key in legacy_props):
        return props, None
    props = dict(props)
    payload = props.pop(ALIAS_PAYLOAD_KEY, None)
    for key in legacy_props:
        props.pop(key, None)
    return props, payload
