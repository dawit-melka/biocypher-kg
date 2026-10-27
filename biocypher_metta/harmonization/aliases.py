"""Typed alias payload carried on emitted nodes, and alias node identity."""

import hashlib
import unicodedata
from typing import Iterable, Iterator, List, NamedTuple, Optional

ALIAS_PAYLOAD_KEY = "_aliases"

IDENTIFIER = "identifier"
NAME = "name"

ENTITY_CLASSES = ("gene", "transcript", "protein", "ontology_term")

# alias_type -> (kind, resolution tier). Only identifier aliases have a tier;
# the tier orders how strongly an alias claims its canonical entity when edge
# endpoints are resolved (lower wins). Names are never used to rewrite edges.
# Versioned IDs are not alias types: curie.normalize strips Ensembl/RefSeq
# versions, so they already resolve to the canonical node directly.
ALIAS_TYPES = {
    "secondary_accession": (IDENTIFIER, 1),
    "alternative_id": (IDENTIFIER, 1),
    "replaced_id": (IDENTIFIER, 1),
    "xref": (IDENTIFIER, 2),
    "entry_name": (IDENTIFIER, 2),
    "preferred_name": (NAME, None),
    "approved_symbol": (NAME, None),
    "previous_symbol": (NAME, None),
    "alias_symbol": (NAME, None),
    "full_name": (NAME, None),
    "other_designation": (NAME, None),
    "exact_synonym": (NAME, None),
    "related_synonym": (NAME, None),
    "broad_synonym": (NAME, None),
    "narrow_synonym": (NAME, None),
    "recommended_name": (NAME, None),
    "alternative_name": (NAME, None),
    "short_name": (NAME, None),
}

# Emitted only when an entry asks for them explicitly via ``alias_types``.
OPT_IN_ALIAS_TYPES = frozenset({"broad_synonym", "narrow_synonym"})


def alias_kind(alias_type: str) -> str:
    return ALIAS_TYPES[alias_type][0]


def resolution_tier(alias_type: str) -> Optional[int]:
    return ALIAS_TYPES[alias_type][1]


class AliasRef(NamedTuple):
    value: str
    alias_type: str
    namespace: Optional[str] = None
    source: Optional[str] = None


class AliasCollector:
    """Accumulates the alias payload for one node, dropping blanks and duplicates.

    The same value from two sources is kept twice so both appear in the
    ``alias_source`` of the resulting ``alias_of`` edge.
    """

    _BLANK = {"", "-"}

    def __init__(self, source: Optional[str] = None):
        self.source = source
        self._refs: List[AliasRef] = []
        self._seen = set()

    def add(self, value, alias_type: str, namespace: Optional[str] = None, source: Optional[str] = None):
        if alias_type not in ALIAS_TYPES:
            raise ValueError(f"Unknown alias_type '{alias_type}'")
        if value is None:
            return
        value = str(value).strip()
        if value in self._BLANK:
            return
        source = source or self.source
        key = (value, alias_type, namespace, source)
        if key in self._seen:
            return
        self._seen.add(key)
        self._refs.append(AliasRef(value, alias_type, namespace, source))

    def extend(self, values: Iterable, alias_type: str, namespace: Optional[str] = None, source: Optional[str] = None):
        for value in values or ():
            self.add(value, alias_type, namespace, source)

    def to_list(self) -> List[AliasRef]:
        return list(self._refs)

    def __iter__(self) -> Iterator[AliasRef]:
        return iter(self._refs)

    def __len__(self) -> int:
        return len(self._refs)


class AliasSelection:
    """Which alias types an adapters-config entry wants (``aliases:`` key)."""

    def __init__(self, alias_types=None, exclude_alias_types=None):
        for name in list(alias_types or []) + list(exclude_alias_types or []):
            if name not in ALIAS_TYPES:
                raise ValueError(f"Unknown alias type '{name}'. Valid: {sorted(ALIAS_TYPES)}")
        self.alias_types = frozenset(alias_types) if alias_types else None
        self.exclude_alias_types = frozenset(exclude_alias_types or ())

    @classmethod
    def from_config(cls, value) -> Optional["AliasSelection"]:
        """``aliases: true`` | ``false`` | ``{alias_types: [...], exclude_alias_types: [...]}``."""
        if value is None or value is False:
            return None
        if value is True:
            return cls()
        if isinstance(value, dict):
            unknown = set(value) - {"alias_types", "exclude_alias_types"}
            if unknown:
                raise ValueError(f"Unknown keys under 'aliases': {sorted(unknown)}")
            return cls(value.get("alias_types"), value.get("exclude_alias_types"))
        raise ValueError(f"'aliases' must be true, false or a mapping, got {value!r}")

    def allows(self, alias_type: str) -> bool:
        if alias_type in self.exclude_alias_types:
            return False
        if self.alias_types is not None:
            return alias_type in self.alias_types
        return alias_type not in OPT_IN_ALIAS_TYPES

    def to_dict(self) -> dict:
        return {
            "alias_types": sorted(self.alias_types) if self.alias_types is not None else None,
            "exclude_alias_types": sorted(self.exclude_alias_types),
        }


def normalize_name(value: str) -> str:
    """Canonical text of a name alias: NFKC, whitespace collapsed, case kept."""
    return " ".join(unicodedata.normalize("NFKC", str(value)).split())


def alias_id(entity_class: str, scope: str, kind: str, value_norm: str) -> str:
    """Deterministic, writer-safe alias node ID.

    No colon and no spaces, so every writer's ``preprocess_id`` keeps the node
    and its ``alias_of`` edges in agreement with or without --include-curie.
    """
    key = "\x1f".join((entity_class, str(scope or ""), kind, value_norm))
    return "ALIAS_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:20].upper()
