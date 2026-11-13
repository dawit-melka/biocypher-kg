"""Alias shards, the merged registry, and edge-endpoint resolution (network-free)."""

import csv
import os

import pytest
import yaml

from biocypher_metta.harmonization.aliases import (
    ALIAS_PAYLOAD_KEY,
    AliasCollector,
    AliasRef,
    AliasSelection,
    alias_id,
)
from biocypher_metta.harmonization.registry import RegistryReader, build_registry
from biocypher_metta.harmonization.resolver import EdgeEndpointHarmonizer
from biocypher_metta.harmonization.schema_info import SchemaInfo
from biocypher_metta.harmonization.shard import AliasCollisionError, AliasShard, read_shard_meta, strip_alias_payload

_SCHEMA = {
    "gene": {"represented_as": "node", "input_label": "gene", "is_a": "coding element"},
    "transcript": {"represented_as": "node", "input_label": "transcript"},
    "protein": {"represented_as": "node", "input_label": "protein"},
    "ontology term": {"represented_as": "node", "input_label": "ontology term"},
    "biological process": {"represented_as": "node", "input_label": "biological_process", "is_a": "ontology term"},
    "molecular function": {"represented_as": "node", "input_label": "molecular_function", "is_a": "ontology term"},
    "pathway": {"represented_as": "node", "input_label": "pathway", "is_a": "biological process"},
    "motif": {"represented_as": "node", "input_label": "motif"},
}
_EDGE_TYPES = {
    "gene_to_process": {"source": "gene", "target": "biological_process", "output_label": None},
    "gene_to_term": {"source": "gene", "target": "ontology_term", "output_label": None},
    "protein_interacts": {"source": "protein", "target": "protein", "output_label": None},
    "motif_binds_gene": {"source": "motif", "target": "gene", "output_label": None},
}


@pytest.fixture
def schema_info(tmp_path):
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump(_SCHEMA))
    return SchemaInfo.from_schema_file(path, _EDGE_TYPES)


def _gene_shard(tmp_path, schema_info, name="gencode_gene", nodes=None, selection=None):
    shard = AliasShard(tmp_path / "shards", name, selection or AliasSelection(), schema_info, default_scope=9606)
    for node_id, label, refs in nodes:
        shard.record_node(node_id, label, {"taxon_id": 9606}, refs)
    return shard


TP53 = ("ENSEMBL:ENSG00000141510", "gene", [
    AliasRef("TP53", "approved_symbol", None, "HGNC"),
    AliasRef("p53", "alias_symbol", None, "HGNC"),
    AliasRef("11998", "xref", "HGNC", "HGNC"),
    AliasRef("7157", "xref", "NCBIGene", "NCBI Gene"),
    AliasRef("ENSG00000141510.18", "xref", "ENSEMBL", "GENCODE"),  # same identifier as the node
])
MDM2 = ("ENSEMBL:ENSG00000135679", "gene", [
    AliasRef("MDM2", "approved_symbol", None, "HGNC"),
    AliasRef("p53", "alias_symbol", None, "HGNC"),     # shared name alias
    AliasRef("4193", "xref", "NCBIGene", "NCBI Gene"),
])


def test_schema_info_classes(schema_info):
    assert schema_info.entity_class("gene") == "gene"
    assert schema_info.entity_class("biological_process") == "ontology_term"
    assert schema_info.entity_class("pathway") == "ontology_term"
    assert schema_info.entity_class("motif") is None
    assert schema_info.concrete_labels("ontology term") == {"ontology_term", "biological_process", "molecular_function", "pathway"}
    assert schema_info.endpoint_types("gene_to_process", "target") == {"biological_process", "pathway"}


def test_alias_id_is_deterministic_and_scoped():
    a = alias_id("gene", "9606", "name", "p53")
    assert a == alias_id("gene", "9606", "name", "p53")
    assert a.startswith("ALIAS_") and ":" not in a and len(a) == 26
    assert a != alias_id("gene", "10090", "name", "p53")
    assert a != alias_id("protein", "9606", "name", "p53")


def test_collector_dedups_and_skips_blanks():
    c = AliasCollector(source="HGNC")
    c.extend(["TP53", "TP53", "-", "", None, " p53 "], "alias_symbol")
    assert [r.value for r in c] == ["TP53", "p53"]
    assert all(r.source == "HGNC" for r in c)
    with pytest.raises(ValueError):
        c.add("x", "not_a_type")


def test_selection_defaults_and_filters():
    default = AliasSelection()
    assert default.allows("exact_synonym") and not default.allows("broad_synonym")
    only = AliasSelection.from_config({"alias_types": ["xref", "broad_synonym"]})
    assert only.allows("broad_synonym") and not only.allows("approved_symbol")
    excluded = AliasSelection.from_config({"exclude_alias_types": ["full_name"]})
    assert not excluded.allows("full_name") and excluded.allows("xref")
    assert AliasSelection.from_config(False) is None
    with pytest.raises(ValueError):
        AliasSelection.from_config({"alias_types": ["bogus"]})


def test_strip_alias_payload_does_not_mutate():
    props = {"gene_name": "TP53", "synonym": ["p53"], ALIAS_PAYLOAD_KEY: [AliasRef("p53", "alias_symbol")]}
    stripped, payload = strip_alias_payload(props, ("synonym",))
    assert stripped == {"gene_name": "TP53"}
    assert payload == [AliasRef("p53", "alias_symbol")]
    assert "synonym" in props and ALIAS_PAYLOAD_KEY in props
    untouched = {"gene_name": "X"}
    assert strip_alias_payload(untouched, ("synonym",)) == (untouched, None)


def test_shard_emits_alias_nodes_and_edges(tmp_path, schema_info):
    shard = _gene_shard(tmp_path, schema_info, nodes=[TP53, MDM2])
    nodes = {node_id: props for node_id, _, props in shard.iter_alias_nodes()}
    edges = list(shard.iter_alias_of_edges(source="GENCODE", source_url="https://www.gencodegenes.org/"))

    by_name = {(p["alias_kind"], p.get("namespace"), p["name"]): aid for aid, p in nodes.items()}
    # The versioned Ensembl xref equals the node itself and is dropped.
    assert ("identifier", "ENSEMBL", "ENSG00000141510") not in by_name
    assert ("identifier", "HGNC", "11998") in by_name
    p53 = by_name[("name", None, "p53")]
    assert nodes[p53] == {"name": "p53", "normalized_name": "p53", "alias_kind": "name", "entity_type": "gene", "scope": "9606"}

    targets = {tgt for src, tgt, _, _ in edges if src == ("alias", p53)}
    assert targets == {("gene", "ENSEMBL:ENSG00000141510"), ("gene", "ENSEMBL:ENSG00000135679")}
    for src, tgt, label, props in edges:
        assert label == "alias_of" and src[0] == "alias"
        assert props["source"] == "GENCODE" and props["alias_type"]

    path = shard.finalize({"format": 1})
    meta = read_shard_meta(path)
    assert meta["labels"] == ["gene"]
    assert meta["summary"]["canonical_nodes"] == 2
    assert not path.with_name(path.name + ".tmp").exists()


def test_selection_filters_payload(tmp_path, schema_info):
    shard = _gene_shard(tmp_path, schema_info, nodes=[TP53], selection=AliasSelection(alias_types=["xref"]))
    kinds = {p["alias_kind"] for _, _, p in shard.iter_alias_nodes()}
    assert kinds == {"identifier"}


def test_collision_guard(tmp_path, schema_info, monkeypatch):
    import biocypher_metta.harmonization.shard as shard_module
    monkeypatch.setattr(shard_module, "alias_id", lambda *args: "ALIAS_SAME")
    shard = _gene_shard(tmp_path, schema_info, nodes=[TP53])
    with pytest.raises(AliasCollisionError):
        shard.summary()


def _registry(tmp_path, schema_info):
    gene = _gene_shard(tmp_path, schema_info, nodes=[TP53, MDM2])
    gene_path = gene.finalize({"format": 1, "adapter": "gene"})

    go = AliasShard(tmp_path / "shards", "go_bp", AliasSelection(), schema_info)
    go.record_node("GO:0008150", "biological_process", {}, [
        AliasRef("GO:0000004", "alternative_id"),
        AliasRef("GO:0007582", "replaced_id"),
        AliasRef("biological_process", "exact_synonym"),
    ])
    go.record_node("GO:0003674", "biological_process", {}, [AliasRef("GO:0005554", "alternative_id")])
    go_path = go.finalize({"format": 1, "adapter": "go"})

    proteins = AliasShard(tmp_path / "shards", "uniprot", AliasSelection(), schema_info, default_scope=9606)
    proteins.record_node("P04637", "protein", {}, [
        AliasRef("Q15086", "secondary_accession", "UniProtKB"),
        AliasRef("ENSP00000269305", "xref", "ENSEMBL"),
        AliasRef("SHARED1", "xref", "TEST"),
    ])
    proteins.record_node("P38398", "protein", {}, [
        AliasRef("Q15086", "xref", "UniProtKB"),       # same key, weaker tier
        AliasRef("SHARED1", "xref", "TEST"),           # same key, same tier -> ambiguous
    ])
    protein_path = proteins.finalize({"format": 1, "adapter": "uniprot"})

    stats = build_registry({"gene": gene_path, "go_bp": go_path, "uniprot": protein_path}, tmp_path / "registry.db")
    return RegistryReader(tmp_path / "registry.db"), stats


def test_registry_stats(tmp_path, schema_info):
    _, stats = _registry(tmp_path, schema_info)
    assert stats["canonical_ids_by_entity_class"] == {"gene": 2, "ontology_term": 2, "protein": 2}
    assert stats["ambiguous_identifier_keys"] == 1   # TEST:SHARED1
    assert stats["fingerprint"]


def _harmonize(tmp_path, schema_info, edges):
    reader, _ = _registry(tmp_path, schema_info)
    harmonizer = EdgeEndpointHarmonizer(reader, schema_info, "test_adapter")
    return list(harmonizer.wrap(edges)), harmonizer


def test_edge_statuses(tmp_path, schema_info):
    edges = [
        # unchanged / normalized / resolved
        ("ENSEMBL:ENSG00000141510", "GO:0008150", "gene_to_process", {}),
        ("Ensembl:ENSG00000141510.18", "GO:0000004", "gene_to_process", {}),
        ("NCBIGene:7157", "http://purl.obolibrary.org/obo/GO_0007582", "gene_to_process", {}),
        ("HGNC:HGNC:11998", "GO:0005554", "gene_to_process", {}),
        # unresolved
        ("ENSEMBL:ENSG00000000000", "GO:9999999", "gene_to_process", {}),
        # names never resolve
        ("p53", "GO:0008150", "gene_to_process", {}),
    ]
    out, h = _harmonize(tmp_path, schema_info, edges)
    assert out[0][:2] == ("ENSEMBL:ENSG00000141510", "GO:0008150")
    assert out[1][:2] == ("ENSEMBL:ENSG00000141510", "GO:0008150")
    assert out[2][:2] == ("ENSEMBL:ENSG00000141510", "GO:0008150")
    assert out[3][:2] == ("ENSEMBL:ENSG00000141510", "GO:0003674")
    assert out[4][:2] == ("ENSEMBL:ENSG00000000000", "GO:9999999")
    assert out[5][0] == "p53"
    statuses = h.summary()["statuses"]
    assert statuses["unchanged"] == 3
    assert statuses["normalized"] == 1
    assert statuses["resolved"] == 5
    assert statuses["unresolved"] == 3


def test_typed_tuples_and_ambiguity(tmp_path, schema_info):
    edges = [
        (("protein", "UniProtKB:P04637"), ("protein", "Q15086"), "protein_interacts", {"score": 1}),
        (("protein", "ENSP00000269305.5"), ("protein", "TEST:SHARED1"), "protein_interacts", {}),
        ("motif_x", ("gene", "ENSEMBL:ENSG00000135679"), "motif_binds_gene", {}),
    ]
    out, h = _harmonize(tmp_path, schema_info, edges)
    # UniProtKB:P04637 -> bare canonical ID; Q15086 is P04637's secondary accession (tier 1 beats xref tier 2)
    assert out[0] == (("protein", "P04637"), ("protein", "P04637"), "protein_interacts", {"score": 1})
    # ENSP resolved; SHARED1 is ambiguous and kept as-is
    assert out[1][0] == ("protein", "P04637")
    assert out[1][1] == ("protein", "TEST:SHARED1")
    # motif endpoints are not harmonized
    assert out[2][0] == "motif_x"
    summary = h.summary()
    assert summary["statuses"]["ambiguous"] == 1
    assert summary["statuses"]["unmanaged"] == 1


def test_type_mismatch(tmp_path, schema_info):
    # A gene ID used where the schema expects a protein
    out, h = _harmonize(tmp_path, schema_info, [
        (("protein", "ENSEMBL:ENSG00000141510"), ("protein", "P04637"), "protein_interacts", {}),
    ])
    assert out[0][0] == ("protein", "ENSEMBL:ENSG00000141510")
    assert h.summary()["statuses"]["unresolved"] == 1


def test_report_tsv(tmp_path, schema_info):
    _, h = _harmonize(tmp_path, schema_info, [
        ("NCBIGene:7157", "GO:9999999", "gene_to_process", {}),
        ("NCBIGene:7157", "GO:9999999", "gene_to_process", {}),
    ])
    path = h.write_report(tmp_path / "report.tsv")
    with open(path) as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    by_status = {r["status"]: r for r in rows}
    assert by_status["resolved"]["count"] == "2"
    assert by_status["resolved"]["candidates"] == "ENSEMBL:ENSG00000141510"
    assert by_status["unresolved"]["raw_id"] == "GO:9999999"


def test_registry_reader_is_fork_safe(tmp_path, schema_info):
    import pickle
    reader, _ = _registry(tmp_path, schema_info)
    assert reader.lookup("gene", "NCBIGENE:7157")[1]
    clone = pickle.loads(pickle.dumps(reader))
    assert clone.path == reader.path and clone._cache == {}

    pid = os.fork()
    if pid == 0:  # child: must open its own connection
        try:
            ok = clone.lookup("gene", "NCBIGENE:7157")[1] == [(2, "gene", "ENSEMBL:ENSG00000141510")]
        finally:
            os._exit(0 if ok else 1)
    _, status = os.waitpid(pid, 0)
    assert os.WEXITSTATUS(status) == 0
