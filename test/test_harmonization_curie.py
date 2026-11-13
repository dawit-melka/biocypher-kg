"""CURIE normalization used for alias identity and edge-endpoint lookup."""

import pytest

from biocypher_metta.harmonization.curie import Curie, lookup_key, normalize


@pytest.mark.parametrize("raw, entity_class, expected", [
    # prefix spellings
    ("ENSEMBL:ENSG00000141510", "gene", ("ENSEMBL", "ENSG00000141510")),
    ("Ensembl:ENSG00000141510", "gene", ("ENSEMBL", "ENSG00000141510")),
    ("ensembl:ensg00000141510", "gene", ("ENSEMBL", "ENSG00000141510")),
    ("UniProt:P04637", "protein", ("UniProtKB", "P04637")),
    ("UniProtKB:P04637", "protein", ("UniProtKB", "P04637")),
    ("GeneID:7157", "gene", ("NCBIGene", "7157")),
    ("Entrez:7157", "gene", ("NCBIGene", "7157")),
    ("FLYBASE:FBgn0038542", "gene", ("FlyBase", "FBgn0038542")),
    # double prefixes from NCBI dbXrefs
    ("HGNC:HGNC:11998", "gene", ("HGNC", "11998")),
    # versions stripped, _PAR_Y kept, isoforms kept
    ("ENSEMBL:ENSG00000141510.18", "gene", ("ENSEMBL", "ENSG00000141510")),
    ("ENSEMBL:ENSG00000182378.15_PAR_Y", "gene", ("ENSEMBL", "ENSG00000182378_PAR_Y")),
    ("ENST00000269305.9", "transcript", ("ENSEMBL", "ENST00000269305")),
    ("RefSeq:NM_000546.6", "transcript", ("RefSeq", "NM_000546")),
    ("OTTHUMG00000162125.10", "gene", ("HAVANA", "OTTHUMG00000162125")),
    ("P04637-2", "protein", ("UniProtKB", "P04637-2")),
    # bare IDs inferred per entity class
    ("P04637", "protein", ("UniProtKB", "P04637")),
    ("ENSP00000269305", "protein", ("ENSEMBL", "ENSP00000269305")),
    ("FBgn0038542", "gene", ("FlyBase", "FBgn0038542")),
    ("WBGene00000001", "gene", ("WormBase", "WBGene00000001")),
    # OBO forms
    ("GO:0008150", "ontology_term", ("GO", "0008150")),
    ("GO_0008150", "ontology_term", ("GO", "0008150")),
    ("http://purl.obolibrary.org/obo/GO_0008150", "ontology_term", ("GO", "0008150")),
    ("http://www.ebi.ac.uk/efo/EFO_0000001", "ontology_term", ("EFO", "0000001")),
])
def test_normalize(raw, entity_class, expected):
    assert normalize(raw, entity_class) == Curie(*expected)


@pytest.mark.parametrize("raw, entity_class", [
    ("tumor protein p53", "gene"),     # free text
    ("TP53", "gene"),                  # symbol without namespace
    ("7157", "gene"),                  # bare number: namespace unknowable
    ("P04637", "gene"),                # UniProt-shaped, but not a protein endpoint
    ("", "gene"),
    (None, "gene"),
])
def test_unparseable(raw, entity_class):
    assert normalize(raw, entity_class) is None


def test_lookup_key_unifies_spellings():
    keys = {
        lookup_key("UniProtKB:P04637", "protein"),
        lookup_key("UniProt:P04637", "protein"),
        lookup_key("P04637", "protein"),
        lookup_key("uniprot:p04637", "protein"),
    }
    assert keys == {"UNIPROTKB:P04637"}
    assert lookup_key("ENSEMBL:ENSG00000141510.18", "gene") == lookup_key("Ensembl:ENSG00000141510", "gene")
