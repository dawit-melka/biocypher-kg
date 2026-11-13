"""Schema facts the harmonization layer needs, as a small picklable object."""

import hashlib
import json
from typing import Dict, Iterable, Optional, Set

import yaml

from .aliases import ENTITY_CLASSES

_DIRECT_CLASSES = {"gene": "gene", "transcript": "transcript", "protein": "protein"}
_ONTOLOGY_ROOT = "ontology_term"
# Edge types that link an entity to another identifier on purpose; rewriting
# their endpoints would collapse e.g. protein->ENSP xrefs into self-loops.
_IDENTIFIER_LINK_ROOTS = {"has_xref", "alias_of"}


def norm_label(label: str) -> str:
    """Same normalization as BaseWriter.normalize_label."""
    if not label:
        return ""
    if "." in label:
        label = label.split(".")[-1]
    return label.lower().replace(" ", "_")


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class SchemaInfo:
    """Node-type hierarchy and edge endpoint types, keyed by normalized labels.

    ``edge_types`` is the ``preprocess_schema`` output already passed to workers.
    """

    def __init__(self, nodes: Dict[str, dict], edge_types: Optional[Dict[str, dict]] = None,
                 raw_entries: Optional[Dict[str, dict]] = None):
        # schema name (normalized) -> {"label": normalized input_label, "parents": [...]}
        self._nodes = nodes
        self.edge_types = edge_types or {}
        # schema name (normalized) -> raw YAML entry, for shard fingerprints
        self._raw = raw_entries or {}
        self._children: Dict[str, Set[str]] = {}
        for name, info in nodes.items():
            for parent in info["parents"]:
                self._children.setdefault(parent, set()).add(name)
        self._label_to_name = {info["label"]: name for name, info in nodes.items()}
        self.identifier_link_labels = self._identifier_link_labels()

    def _identifier_link_labels(self) -> Set[str]:
        edges = {name: entry for name, entry in self._raw.items() if entry.get("represented_as") == "edge"}
        labels = set()
        for name, entry in edges.items():
            lineage, current, seen = {name}, name, set()
            while current in edges and current not in seen:
                seen.add(current)
                parents = [norm_label(p) for p in _as_list(edges[current].get("is_a"))]
                if not parents:
                    break
                lineage.update(parents)
                current = parents[0]
            if lineage & _IDENTIFIER_LINK_ROOTS:
                for label in _as_list(entry.get("input_label") or name):
                    labels.add(norm_label(label))
        return labels

    @classmethod
    def from_schema_file(cls, schema_path, edge_types: Optional[Dict[str, dict]] = None) -> "SchemaInfo":
        with open(schema_path) as f:
            raw = yaml.safe_load(f) or {}
        nodes = {}
        raw_entries = {}
        for name, entry in raw.items():
            if not isinstance(entry, dict):
                continue
            raw_entries[norm_label(name)] = entry
            if entry.get("represented_as") != "node":
                continue
            input_label = entry.get("input_label") or name
            if isinstance(input_label, list):
                input_label = input_label[0]
            nodes[norm_label(name)] = {
                "label": norm_label(input_label),
                "parents": [norm_label(p) for p in _as_list(entry.get("is_a"))],
            }
        return cls(nodes, edge_types, raw_entries)

    def _name_for(self, type_name: str) -> Optional[str]:
        key = norm_label(type_name)
        if key in self._nodes:
            return key
        return self._label_to_name.get(key)

    def _ancestors(self, name: str) -> Set[str]:
        seen, stack = set(), [name]
        while stack:
            current = stack.pop()
            for parent in self._nodes.get(current, {}).get("parents", []):
                if parent not in seen:
                    seen.add(parent)
                    stack.append(parent)
        return seen

    def entity_class(self, node_type: str) -> Optional[str]:
        """gene | transcript | protein | ontology_term, or None for other node types."""
        name = self._name_for(node_type)
        if name is None:
            return None
        lineage = {name} | self._ancestors(name)
        for direct, cls in _DIRECT_CLASSES.items():
            if direct in lineage:
                return cls
        if _ONTOLOGY_ROOT in lineage:
            return "ontology_term"
        return None

    def concrete_labels(self, type_name: str) -> Set[str]:
        """Emitted node labels a schema type covers: itself plus every descendant."""
        name = self._name_for(type_name)
        if name is None:
            return {norm_label(type_name)}
        labels, stack = set(), [name]
        while stack:
            current = stack.pop()
            labels.add(self._nodes[current]["label"])
            stack.extend(self._children.get(current, ()))
        return labels

    def endpoint_types(self, edge_label: str, role: str) -> Set[str]:
        """Concrete node labels allowed at ``role`` ('source'/'target') of an edge label."""
        info = self.edge_types.get(norm_label(edge_label))
        if not info:
            return set()
        labels = set()
        for type_name in _as_list(info.get(role)):
            labels |= self.concrete_labels(type_name)
        return labels

    def harmonizable_labels(self) -> Set[str]:
        return {info["label"] for name, info in self._nodes.items() if self.entity_class(name) in ENTITY_CLASSES}

    def ontology_term_labels(self) -> Iterable[str]:
        return sorted(
            info["label"] for name, info in self._nodes.items()
            if self.entity_class(name) == "ontology_term" and name != _ONTOLOGY_ROOT
        )

    def digest(self, labels: Iterable[str]) -> str:
        """Stable hash of the schema entries for these node labels plus the alias model."""
        names = {self._name_for(label) or norm_label(label) for label in labels}
        names |= {"alias", "alias_of"}
        payload = {name: self._raw.get(name) for name in sorted(names)}
        blob = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
