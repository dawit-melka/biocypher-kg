"""Shard fingerprints: what a shard was built from, so a stale one is never merged.

A fingerprint records the adapter's identity and resolved constructor args,
size+mtime of every input path among those args, the entry's ``aliases:``
selection, a digest of the schema entries it emitted, and the version stamps
of processor caches the adapter's aliases depend on.
"""

import hashlib
import json
import os
from typing import Dict, Iterable, List, Optional

from .aliases import AliasSelection
from .schema_info import SchemaInfo

SHARD_FORMAT_VERSION = 1

# Injected by the pipeline at run time; they do not change what a shard records.
_RUNTIME_ARGS = frozenset({"dbsnp_rsid_map", "dbsnp_pos_map", "write_properties", "add_provenance"})


def _iter_path_values(value) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_path_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_path_values(item)


def _path_stats(args: dict) -> Dict[str, list]:
    """size + mtime of every regular file named in the args.

    Directories are skipped: their mtime changes whenever any file in them is
    replaced (e.g. a shared ontology cache dir) and says nothing about in-place
    edits. Adapters whose real inputs live in a directory declare them through
    ``alias_fingerprint_deps`` instead.
    """
    stats = {}
    for value in args.values():
        for candidate in _iter_path_values(value):
            if candidate and os.path.isfile(candidate):
                st = os.stat(candidate)
                stats[candidate] = [st.st_size, st.st_mtime_ns]
    return dict(sorted(stats.items()))


def _jsonable(value):
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def adapter_args(entry: dict) -> dict:
    args = (entry.get("adapter") or {}).get("args") or {}
    return {k: v for k, v in args.items() if k not in _RUNTIME_ARGS}


def adapter_fingerprint(name: str, entry: dict, selection: AliasSelection, schema_info: SchemaInfo,
                        labels: Iterable[str], deps: Optional[dict] = None) -> dict:
    adapter = entry.get("adapter") or {}
    args = adapter_args(entry)
    return {
        "format": SHARD_FORMAT_VERSION,
        "adapter": name,
        "module": adapter.get("module"),
        "cls": adapter.get("cls"),
        "args": _jsonable(args),
        "files": _path_stats(args),
        "aliases": selection.to_dict(),
        "schema": schema_info.digest(labels),
        "deps": _jsonable(deps or {}),
    }


def digest(fingerprint: dict) -> str:
    blob = json.dumps(fingerprint, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def diff(old: dict, new: dict) -> List[str]:
    """Top-level fields that differ between two fingerprints."""
    return sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))


def version_stamp(version_json_path) -> Optional[str]:
    """``timestamp`` of a BaseMappingProcessor ``*_version.json``, or None."""
    try:
        with open(version_json_path) as f:
            return json.load(f).get("timestamp")
    except (OSError, ValueError):
        return None
