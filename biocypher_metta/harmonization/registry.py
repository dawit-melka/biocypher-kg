"""Run-level registry of canonical IDs and identifier aliases, merged from shards."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from biocypher._logger import logger

from biocypher_metta.sqlite_conn_cache import SQLiteConnCache

from . import fingerprint as fp

_SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE canonical (
    entity_class TEXT NOT NULL,
    norm_key     TEXT NOT NULL,
    node_type    TEXT NOT NULL,
    emitted_id   TEXT NOT NULL,
    adapter      TEXT NOT NULL
);
CREATE TABLE id_alias (
    entity_class TEXT NOT NULL,
    norm_key     TEXT NOT NULL,
    tier         INTEGER NOT NULL,
    node_type    TEXT NOT NULL,
    emitted_id   TEXT NOT NULL,
    adapter      TEXT NOT NULL
);
"""


def build_registry(shards: Dict[str, Path], out_path) -> dict:
    """Merge finished shards into ``out_path`` and return registry statistics.

    Callers verify shard fingerprints first (see ``verify_shards``).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    # URI mode so shards can be ATTACHed read-only.
    conn = sqlite3.connect(tmp_path.resolve().as_uri(), uri=True)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.executescript(_SCHEMA)
    fingerprints = {}
    for adapter, shard_path in sorted(shards.items()):
        conn.execute("ATTACH DATABASE ? AS s", (Path(shard_path).resolve().as_uri() + "?mode=ro",))
        conn.execute(
            "INSERT INTO canonical SELECT entity_class, norm_key, node_type, emitted_id, ? FROM s.canonical",
            (adapter,),
        )
        conn.execute(
            "INSERT INTO id_alias "
            "SELECT DISTINCT a.entity_class, a.norm_key, l.tier, l.node_type, l.emitted_id, ? "
            "FROM s.link l JOIN s.alias a ON a.alias_id = l.alias_id "
            "WHERE a.kind = 'identifier' AND l.tier IS NOT NULL",
            (adapter,),
        )
        shard_fp = conn.execute("SELECT value FROM s.meta WHERE key = 'fingerprint'").fetchone()
        fingerprints[adapter] = fp.digest(json.loads(shard_fp[0])) if shard_fp else None
        conn.commit()
        conn.execute("DETACH DATABASE s")

    conn.executescript(
        "CREATE INDEX idx_canonical ON canonical (entity_class, norm_key);"
        "CREATE INDEX idx_id_alias ON id_alias (entity_class, norm_key);"
    )
    stats = _registry_stats(conn)
    registry_fp = fp.digest(fingerprints)
    stats["fingerprint"] = registry_fp
    stats["shards"] = sorted(shards)
    conn.executemany(
        "INSERT INTO meta VALUES (?, ?)",
        [("fingerprint", registry_fp), ("shards", json.dumps(fingerprints, sort_keys=True))],
    )
    conn.commit()
    conn.close()
    SQLiteConnCache.drop(str(out_path))
    os.replace(tmp_path, out_path)
    logger.info(
        f"Alias registry: {stats['canonical_ids']:,} canonical IDs, "
        f"{stats['identifier_alias_keys']:,} identifier aliases "
        f"({stats['ambiguous_identifier_keys']:,} ambiguous) from {len(shards)} shard(s)"
    )
    return stats


def _registry_stats(conn) -> dict:
    canonical = dict(conn.execute(
        "SELECT entity_class, COUNT(*) FROM canonical GROUP BY entity_class ORDER BY entity_class"
    ).fetchall())
    keys = conn.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT entity_class, norm_key FROM id_alias)"
    ).fetchone()[0]
    # Ambiguous: more than one canonical entity at the lowest tier with a match.
    ambiguous = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT a.entity_class, a.norm_key
            FROM id_alias a
            JOIN (SELECT entity_class, norm_key, MIN(tier) AS tier FROM id_alias GROUP BY 1, 2) m
              ON a.entity_class = m.entity_class AND a.norm_key = m.norm_key AND a.tier = m.tier
            GROUP BY a.entity_class, a.norm_key
            HAVING COUNT(DISTINCT a.node_type || char(31) || a.emitted_id) > 1
        )
        """
    ).fetchone()[0]
    return {
        "canonical_ids": sum(canonical.values()),
        "canonical_ids_by_entity_class": canonical,
        "identifier_alias_keys": keys,
        "ambiguous_identifier_keys": ambiguous,
    }


def read_registry_fingerprint(path) -> Optional[str]:
    path = Path(path)
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'fingerprint'").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return row[0] if row else None


class RegistryReader:
    """Read-only lookups against a registry; picklable (holds only the path)."""

    _CACHE_LIMIT = 200_000

    def __init__(self, path):
        self.path = str(path)
        self._cache: Dict[tuple, tuple] = {}
        self._managed = None

    def __getstate__(self):
        return {"path": self.path}

    def __setstate__(self, state):
        self.__init__(state["path"])

    @property
    def _conn(self) -> sqlite3.Connection:
        return SQLiteConnCache.get(self.path)

    def managed_node_types(self) -> frozenset:
        if self._managed is None:
            self._managed = frozenset(r[0] for r in self._conn.execute("SELECT DISTINCT node_type FROM canonical"))
        return self._managed

    def lookup(self, entity_class: str, norm_key: str) -> Tuple[List[tuple], List[tuple]]:
        """(canonical matches, identifier-alias matches) for one key.

        Canonical matches are (node_type, emitted_id); alias matches are
        (tier, node_type, emitted_id).
        """
        cache_key = (entity_class, norm_key)
        hit = self._cache.get(cache_key)
        if hit is not None:
            return hit
        canonical = self._conn.execute(
            "SELECT DISTINCT node_type, emitted_id FROM canonical WHERE entity_class = ? AND norm_key = ?",
            cache_key,
        ).fetchall()
        aliases = [] if canonical else self._conn.execute(
            "SELECT DISTINCT tier, node_type, emitted_id FROM id_alias WHERE entity_class = ? AND norm_key = ?",
            cache_key,
        ).fetchall()
        if len(self._cache) >= self._CACHE_LIMIT:
            self._cache.clear()
        result = (canonical, aliases)
        self._cache[cache_key] = result
        return result
