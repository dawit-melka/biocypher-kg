"""Fake adapters for the harmonization pipeline tests.

A module (not test-local classes) so forked ProcessPoolExecutor workers can
import them by name from the adapters config.
"""

import os

from biocypher_metta.adapters import Adapter
from biocypher_metta.harmonization.aliases import ALIAS_PAYLOAD_KEY, AliasCollector

GENES = [
    ("ENSG00000141510", "TP53", "HGNC:11998", ["p53", "LFS1"]),
    ("ENSG00000135679", "MDM2", "HGNC:6973", ["p53"]),  # shares the 'p53' alias with TP53
]


class FakeGeneAdapter(Adapter):
    """Gene nodes with a flat synonym list (legacy) and a typed alias payload."""

    SUPPORTS_ALIASES = True
    ALIAS_LEGACY_PROPS = ("synonym",)

    def __init__(self, write_properties, add_provenance, label="gene", taxon_id=9606,
                 edge_label="coexpressed_with"):
        self.label = label
        self.taxon_id = taxon_id
        self.edge_label = edge_label
        self.source = "FAKE_GENES"
        self.source_url = "http://fake.genes"
        super().__init__(write_properties, add_provenance)

    def get_nodes(self):
        for gene_id, symbol, hgnc_id, synonyms in GENES:
            props = {}
            if self.write_properties:
                props = {"gene_name": symbol, "synonym": [symbol] + synonyms, "taxon_id": self.taxon_id}
            if self.emit_aliases:
                aliases = AliasCollector(source="HGNC")
                aliases.add(symbol, "approved_symbol")
                aliases.add(hgnc_id, "xref", "HGNC")
                aliases.extend(synonyms, "alias_symbol")
                props[ALIAS_PAYLOAD_KEY] = aliases.to_list()
            yield f"ENSEMBL:{gene_id}", self.label, props

    def get_edges(self):
        # Only resolvable through the HGNC ID aliases of this adapter's own nodes.
        yield "HGNC:11998", "HGNC:6973", self.edge_label, {}


class FakeEdgeAdapter(Adapter):
    """Edges referencing genes by alternate spellings and aliases."""

    def __init__(self, write_properties, add_provenance, label="coexpressed_with", fail_marker=None):
        self.label = label
        self.fail_marker = fail_marker
        self.source = "FAKE_EDGES"
        self.source_url = "http://fake.edges"
        super().__init__(write_properties, add_provenance)

    def get_nodes(self):
        return iter(())

    def get_edges(self):
        if self.fail_marker and os.path.exists(self.fail_marker):
            raise RuntimeError("fake edge adapter failure")
        yield "HGNC:HGNC:11998", "Ensembl:ENSG00000135679.12", self.label, {}  # resolved + normalized
        yield "ENSEMBL:ENSG00000000001", "ENSEMBL:ENSG00000141510", self.label, {}  # unresolved + unchanged
        yield "p53", "ENSEMBL:ENSG00000141510", self.label, {}  # names never resolve


class FakeMultiTypeAdapter(Adapter):
    """A protein and a GO term, so alias_of edges target several node types."""

    SUPPORTS_ALIASES = True
    ALIAS_LEGACY_PROPS = ("accessions", "synonym", "alternative_ids")

    def __init__(self, write_properties, add_provenance, taxon_id=9606):
        self.taxon_id = taxon_id
        self.source = "FAKE_MULTI"
        self.source_url = "http://fake.multi"
        super().__init__(write_properties, add_provenance)

    def get_nodes(self):
        protein = {"protein_name": "P53", "accessions": ["Q15086"]} if self.write_properties else {}
        term = {"term_name": "biological_process", "alternative_ids": ["GO:0000004"]} if self.write_properties else {}
        if self.emit_aliases:
            aliases = AliasCollector(source="UniProt")
            aliases.add("Q15086", "secondary_accession", "UniProtKB")
            aliases.add("P53_HUMAN", "entry_name", "UniProtKB")
            aliases.add("Cellular tumor antigen p53", "recommended_name")
            protein[ALIAS_PAYLOAD_KEY] = aliases.to_list()
            aliases = AliasCollector(source="Gene Ontology")
            aliases.add("GO:0000004", "alternative_id")
            aliases.add("physiological process", "exact_synonym")
            term[ALIAS_PAYLOAD_KEY] = aliases.to_list()
        yield "P04637", "protein", protein
        yield "GO:0008150", "biological_process", term
