"""Entity harmonization: alias nodes, ``alias_of`` edges and edge-endpoint resolution.

Adapters that already emit canonical nodes (genes, transcripts, proteins,
ontology terms) can attach a typed alias payload to each node. When aliases are
enabled for that adapter in the adapters config, the pipeline:

1. strips the payload (and the adapter's legacy flat alias properties) from the
   node, records it in a per-adapter SQLite shard, and writes ``alias`` nodes
   plus ``alias_of`` edges pointing at the emitted node;
2. merges the shards into a registry of canonical IDs and identifier aliases;
3. rewrites edge endpoints of every other adapter that reference a canonical
   entity through an unambiguous identifier alias (keep-as-is + report
   otherwise).
"""

from .aliases import (
    ALIAS_PAYLOAD_KEY,
    ALIAS_TYPES,
    AliasCollector,
    AliasRef,
    AliasSelection,
)

__all__ = [
    "ALIAS_PAYLOAD_KEY",
    "ALIAS_TYPES",
    "AliasCollector",
    "AliasRef",
    "AliasSelection",
]
