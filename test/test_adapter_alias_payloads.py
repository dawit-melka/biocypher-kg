"""Typed alias payloads emitted by real adapters, from data they already parse.

Network-free: ontology graphs are pre-seeded into OntologyAdapter's load cache,
GENCODE/UniProt inputs are tiny fixtures or the committed samples.
"""

import gzip

import pytest
import rdflib

import biocypher_metta.adapters.gencode_gene_adapter as gencode_gene_module
from biocypher_metta.adapters.cell_ontology_adapter import CellOntologyAdapter
from biocypher_metta.adapters.gencode_gene_adapter import GencodeGeneAdapter
from biocypher_metta.adapters.gencode_transcript_adapter import GencodeTranscriptAdapter
from biocypher_metta.adapters.gene_ontology_adapter import GeneOntologyAdapter
from biocypher_metta.adapters.ontologies_adapter import OntologyAdapter
from biocypher_metta.adapters.uberon_adapter import UberonAdapter
from biocypher_metta.adapters.uniprot_protein_adapter import UniprotProteinAdapter
from biocypher_metta.harmonization.aliases import ALIAS_PAYLOAD_KEY, AliasSelection
from biocypher_metta.harmonization.shard import strip_alias_payload

LEGACY_ALIAS_PROPS = {"synonym", "alternative_ids", "accessions"}

_UBERON_TTL = """
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix oio: <http://www.geneontology.org/formats/oboInOwl#> .

obo:UBERON_0000948 a owl:Class ; rdfs:label "heart" ;
    oio:hasExactSynonym "cardium" ; oio:hasRelatedSynonym "chambered heart" ;
    oio:hasBroadSynonym "pump" ; oio:hasAlternativeId "UBERON:0007100" .
obo:UBERON_0000001 a owl:Class ; rdfs:label "obsolete a" ; owl:deprecated true ;
    obo:IAO_0100001 obo:UBERON_0000002 .
obo:UBERON_0000002 a owl:Class ; rdfs:label "obsolete b" ; owl:deprecated true ;
    obo:IAO_0100001 "UBERON:0000948" .
obo:UBERON_0000003 a owl:Class ; rdfs:label "obsolete c" ; owl:deprecated true ;
    obo:IAO_0100001 "http://purl.obolibrary.org/obo/UBERON_0000948" .
obo:CL_0000000 a owl:Class ; rdfs:label "cell" ; oio:hasExactSynonym "imported synonym" .
"""

_GO_TTL = """
@prefix obo: <http://purl.obolibrary.org/obo/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix oio: <http://www.geneontology.org/formats/oboInOwl#> .

obo:GO_0008150 a owl:Class ; rdfs:label "biological_process" ; oio:hasAlternativeId "GO:0000004" .
obo:GO_0003674 a owl:Class ; rdfs:label "molecular_function" .
obo:GO_0000005 a owl:Class ; rdfs:label "obsolete bp" ; owl:deprecated true ; obo:IAO_0100001 obo:GO_0008150 .
"""


def _seed(name, ttl):
    graph = rdflib.Graph()
    graph.parse(data=ttl, format="turtle")
    OntologyAdapter._ONTOLOGY_LOAD_CACHE[(name, None)] = (None, graph, "test")
    return graph


@pytest.fixture
def uberon_graph():
    key = ("test_uberon", None)
    _seed("test_uberon", _UBERON_TTL)
    yield
    OntologyAdapter._ONTOLOGY_LOAD_CACHE.pop(key, None)


def _by_id(nodes):
    return {node_id: (label, props) for node_id, label, props in nodes}


def _refs(props):
    return {(r.value, r.alias_type, r.namespace) for r in props.get(ALIAS_PAYLOAD_KEY, [])}


def test_ontology_payload(uberon_graph):
    adapter = UberonAdapter(True, True, "test_uberon", "node", "anatomy")
    adapter.enable_aliases(AliasSelection(alias_types=None))
    nodes = _by_id(adapter.get_nodes())

    _, heart = nodes["UBERON:0000948"]
    assert _refs(heart) == {
        ("heart", "preferred_name", None),
        ("cardium", "exact_synonym", None),
        ("chambered heart", "related_synonym", None),
        ("UBERON:0007100", "alternative_id", None),
        # IRI, CURIE-literal and IRI-literal replaced_by forms, plus a 2-hop chain
        ("UBERON:0000001", "replaced_id", None),
        ("UBERON:0000002", "replaced_id", None),
        ("UBERON:0000003", "replaced_id", None),
    }
    assert "UBERON:0000001" not in nodes        # deprecated terms are still not emitted
    _, imported = nodes["CL:0000000"]
    assert _refs(imported) == set()             # imported terms carry no aliases


def test_ontology_broad_synonyms_are_opt_in(uberon_graph):
    adapter = UberonAdapter(True, True, "test_uberon", "node", "anatomy")
    adapter.enable_aliases(AliasSelection(alias_types=["broad_synonym", "exact_synonym"]))
    _, heart = _by_id(adapter.get_nodes())["UBERON:0000948"]
    assert ("pump", "broad_synonym", None) in _refs(heart)


def test_ontology_default_output_unchanged(uberon_graph):
    adapter = UberonAdapter(True, True, "test_uberon", "node", "anatomy")
    _, heart = _by_id(adapter.get_nodes())["UBERON:0000948"]
    assert ALIAS_PAYLOAD_KEY not in heart
    assert sorted(map(str, heart["synonym"])) == ["cardium", "chambered heart"]
    assert list(map(str, heart["alternative_ids"])) == ["UBERON:0007100"]


class _StubGOSubontology:
    mapping = {"GO:0008150": "biological_process", "GO:0003674": "molecular_function",
               "GO:0000005": "biological_process"}

    def set_graph(self, graph):
        pass

    def load_or_update(self):
        return self.mapping


def test_gene_ontology_payload_and_subontology_filter():
    _seed("test_go", _GO_TTL)
    try:
        adapter = GeneOntologyAdapter(True, True, "test_go", "node", "biological_process",
                                      go_subontology_processor=_StubGOSubontology())
        adapter.enable_aliases()
        nodes = list(adapter.get_nodes())
    finally:
        OntologyAdapter._ONTOLOGY_LOAD_CACHE.pop(("test_go", None), None)
    assert [(n, l) for n, l, _ in nodes] == [("GO:0008150", "biological_process")]
    assert _refs(nodes[0][2]) >= {("GO:0000004", "alternative_id", None), ("GO:0000005", "replaced_id", None)}


def test_cell_ontology_keeps_description_quirk():
    ttl = """
    @prefix obo: <http://purl.obolibrary.org/obo/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    obo:CL_0000001 a owl:Class ; rdfs:label "cell a" .
    """
    _seed("test_cl", ttl)
    try:
        adapter = CellOntologyAdapter(True, False, "test_cl", "node", add_description=True)
        nodes = list(adapter.get_nodes())
    finally:
        OntologyAdapter._ONTOLOGY_LOAD_CACHE.pop(("test_cl", None), None)
    # CL writes an (empty) description even when the term has none, unlike the base adapter.
    assert nodes == [("CL:0000001", "cell_type", {"term_name": "cell a", "description": ""})]


_GTF = (
    'chr17\tHAVANA\ttranscript\t7661779\t7687538\t.\t-\t.\tgene_id "ENSG00000141510.18"; '
    'transcript_id "ENST00000269305.9"; gene_type "protein_coding"; gene_name "TP53"; '
    'transcript_type "protein_coding"; transcript_name "TP53-201"; level 2; tag "basic"; '
    'tag "Ensembl_canonical"; tag "MANE_Select"; havana_transcript "OTTHUMT00000367397.3";\n'
)


def test_transcript_payload(tmp_path):
    gtf = tmp_path / "gencode.v49.test.gtf.gz"
    with gzip.open(gtf, "wt") as f:
        f.write(_GTF)
    adapter = GencodeTranscriptAdapter(True, False, 9606, filepath=str(gtf), label="transcript")
    adapter.enable_aliases()
    [(node_id, _, props)] = list(adapter.get_nodes())
    assert node_id == "ENSEMBL:ENST00000269305"
    assert _refs(props) == {("TP53-201", "preferred_name", None), ("OTTHUMT00000367397.3", "xref", "HAVANA")}


def test_uniprot_payload_routes_isoform_xrefs():
    adapter = UniprotProteinAdapter("samples/hsa/uniprot/uniprot_sprot_human.dat.gz", True, False, 9606, "protein")
    adapter.enable_aliases()
    nodes = _by_id(adapter.get_nodes())
    _, base = nodes["Q9UG63"]
    refs = _refs(base)
    assert ("O60864", "secondary_accession", "UniProtKB") in refs
    assert ("ABCF2_HUMAN", "entry_name", "UniProtKB") in refs
    assert ("ABCF2", "approved_symbol", None) in refs
    assert ("ATP-binding cassette sub-family F member 2", "recommended_name", None) in refs
    assert ("ENSP00000287844.2", "xref", "ENSEMBL") in refs     # displayed isoform -> base node
    _, isoform2 = nodes["Q9UG63-2"]
    assert _refs(isoform2) == {("ENSP00000222388.2", "xref", "ENSEMBL")}


class _StubHGNC:
    def load_or_update(self):
        return {}

    def process_identifier(self, identifier):
        return {"status": "current", "original": identifier, "current": identifier}

    def get_symbol_record(self, symbol):
        return {"symbol": symbol, "hgnc_id": "HGNC:5", "name": "alpha-1-B glycoprotein", "entrez_id": "1",
                "previous_symbols": [], "alias_symbols": ["A1B"]}


_GENE_GTF = (
    'chr19\tHAVANA\tgene\t58345178\t58353492\t.\t-\t.\tgene_id "ENSG00000121410.13"; '
    'gene_type "protein_coding"; gene_name "A1BG"; level 2; hgnc_id "HGNC:5"; '
    'havana_gene "OTTHUMG00000183507.1";\n'
)
_GENE_INFO = (
    "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\tdbXrefs\tchromosome\tmap_location\tdescription\ttype_of_gene\t"
    "Symbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\tNomenclature_status\t"
    "Other_designations\tModification_date\tFeature_type\n"
    "9606\t1\tA1BG\t-\tA1B|ABG\tMIM:138670|HGNC:HGNC:5|Ensembl:ENSG00000121410\t19\t19q13.43\t"
    "alpha-1-B glycoprotein\tprotein-coding\tA1BG\talpha-1-B glycoprotein\tO\talpha-1B-glycoprotein\t20240101\t-\n"
)


def _gene_adapter(tmp_path, monkeypatch):
    monkeypatch.setattr(gencode_gene_module, "HGNCProcessor", _StubHGNC)
    gtf, gene_info = tmp_path / "gencode.v49.test.gtf.gz", tmp_path / "Homo_sapiens.gene_info.gz"
    with gzip.open(gtf, "wt") as f:
        f.write(_GENE_GTF)
    with gzip.open(gene_info, "wt") as f:
        f.write(_GENE_INFO)
    return GencodeGeneAdapter(True, False, 9606, str(gtf), "gene", gene_alias_file_path=str(gene_info))


def test_gene_payload_is_typed(tmp_path, monkeypatch):
    adapter = _gene_adapter(tmp_path, monkeypatch)
    adapter.enable_aliases()
    [(_, _, props)] = list(adapter.get_nodes())
    refs = {(r.value, r.alias_type, r.namespace, r.source) for r in props[ALIAS_PAYLOAD_KEY]}
    assert {
        ("A1BG", "approved_symbol", None, "HGNC"),
        ("A1BG", "approved_symbol", None, "NCBI Gene"),
        ("HGNC:5", "xref", "HGNC", "GENCODE"),
        ("OTTHUMG00000183507.1", "xref", "HAVANA", "GENCODE"),
        ("1", "xref", "NCBIGene", "NCBI Gene"),
        ("A1B", "alias_symbol", None, "HGNC"),
        ("ABG", "alias_symbol", None, "NCBI Gene"),
        ("alpha-1-B glycoprotein", "full_name", None, "HGNC"),
        ("alpha-1B-glycoprotein", "other_designation", None, "NCBI Gene"),
    } <= refs


ALIAS_ADAPTERS = [
    ("gencode_gene", lambda tmp_path, monkeypatch, _: _gene_adapter(tmp_path, monkeypatch)),
    ("uniprot", lambda *_: UniprotProteinAdapter("samples/hsa/uniprot/uniprot_sprot_human.dat.gz", True, False, 9606, "protein")),
    ("uberon", lambda *_: UberonAdapter(True, False, "test_uberon", "node", "anatomy")),
]


@pytest.mark.parametrize("name, factory", ALIAS_ADAPTERS, ids=[a[0] for a in ALIAS_ADAPTERS])
def test_alias_mode_strips_every_legacy_prop(name, factory, tmp_path, monkeypatch, uberon_graph):
    plain = factory(tmp_path, monkeypatch, None)
    emitted_legacy = {k for _, _, props in plain.get_nodes() for k in props} & LEGACY_ALIAS_PROPS
    assert emitted_legacy, f"{name}: fixture emits no legacy alias props"
    assert emitted_legacy <= set(type(plain).ALIAS_LEGACY_PROPS)

    aliased = factory(tmp_path, monkeypatch, None)
    aliased.enable_aliases()
    for _, _, props in aliased.get_nodes():
        stripped, _ = strip_alias_payload(props, type(aliased).ALIAS_LEGACY_PROPS)
        assert not (set(stripped) & (LEGACY_ALIAS_PROPS | {ALIAS_PAYLOAD_KEY}))


def test_alias_classes_declare_support():
    for cls in (GencodeGeneAdapter, GencodeTranscriptAdapter, UniprotProteinAdapter,
                OntologyAdapter, GeneOntologyAdapter, CellOntologyAdapter, UberonAdapter):
        assert cls.SUPPORTS_ALIASES
    assert set(OntologyAdapter.ALIAS_LEGACY_PROPS) == {"synonym", "alternative_ids"}
    assert GeneOntologyAdapter.ALIAS_LEGACY_PROPS == OntologyAdapter.ALIAS_LEGACY_PROPS
