"""alias nodes and alias_of edges through every writer.

alias_of is the only schema edge with a list target; this guards the writer
paths that depend on the typed endpoint (file naming, Parquet's per-type
expansion, KGX's property filter) and the alias ID surviving preprocess_id.
"""

import json

import pandas as pd
import pytest

import create_knowledge_graph as ck

WRITERS = ["metta", "neo4j", "parquet", "prolog", "kgx", "networkx"]


@pytest.fixture(scope="module")
def schema():
    merged = ck.merge_schemas("config/primer_schema_config.yaml", "config/hsa/hsa_schema_config.yaml")
    try:
        yield merged, ck.preprocess_schema(merged)
    finally:
        ck.delete_temp_schema(merged)


def _config():
    return {
        "fake_gene": {
            "adapter": {"module": "harmonization_fakes", "cls": "FakeGeneAdapter", "args": {"label": "gene"}},
            "outdir": "fake/gene", "nodes": True, "edges": False, "aliases": True,
        },
        "fake_multi": {
            "adapter": {"module": "harmonization_fakes", "cls": "FakeMultiTypeAdapter", "args": {}},
            "outdir": "fake/multi", "nodes": True, "edges": False, "aliases": True,
        },
    }


@pytest.mark.parametrize("writer_type", WRITERS)
def test_alias_output_per_writer(schema, tmp_path, writer_type):
    schema_path, schema_dict = schema
    config = _config()
    harmonization = ck._setup_harmonization(config, config, schema_path, schema_dict, tmp_path, True, True)
    writer = ck.get_writer(writer_type, tmp_path, schema_path)
    nodes_count, nodes_props, edges_count, *_ = ck.process_adapters(
        config, {}, {}, writer, True, True, schema_dict, skip_preflight=True, harmonization=harmonization,
    )
    if writer_type == "networkx":
        writer.write_graph()
    if hasattr(writer, "finalize"):
        writer.finalize()

    expected_edges = {key.split("|")[-1]: n for key, n in edges_count.items() if key.startswith("alias_of|")}
    assert set(expected_edges) == {"gene", "protein", "biological_process"}
    assert nodes_count["alias"] == sum(r["summary"]["alias_nodes"] for r in harmonization.alias_results.values())

    gene_aliases = tmp_path / "fake/gene/aliases/fake_gene"
    multi_aliases = tmp_path / "fake/multi/aliases/fake_multi"

    if writer_type == "neo4j":
        node_ids = set(pd.read_csv(gene_aliases / "nodes_alias.csv", sep="|")["id"])
        edges = pd.read_csv(gene_aliases / "edges_alias_alias_of_gene.csv", sep="|")
        assert set(edges["source_id"]) <= node_ids
        assert set(edges["target_id"]) == {"ENSG00000141510", "ENSG00000135679"}
        gene_nodes = pd.read_csv(tmp_path / "fake/gene/nodes_gene.csv", sep="|")
        assert "synonym" not in gene_nodes.columns
    elif writer_type == "parquet":
        files = sorted(multi_aliases.glob("edges_alias_of_*.parquet"))
        rows = pd.concat([pd.read_parquet(f) for f in files])
        # one row per alias_of edge: not duplicated across the 19 listed target types
        assert len(rows) == expected_edges["protein"] + expected_edges["biological_process"]
        assert set(rows["target_type"]) == {"protein", "biological_process"}
    elif writer_type == "kgx":
        # KGX drops properties the schema does not declare.
        nodes = pd.read_csv(multi_aliases / "alias_nodes.csv")
        assert {"name", "normalized_name", "alias_kind", "namespace", "entity_type", "scope"} <= set(nodes.columns)
        protein_edges = pd.read_csv(multi_aliases / "alias_of_alias_protein_edges.csv")
        assert len(protein_edges) == expected_edges["protein"]
        assert (multi_aliases / "alias_of_alias_biological_process_edges.csv").exists()
    elif writer_type == "prolog":
        assert (gene_aliases / "nodes.pl").exists() and (gene_aliases / "edges.pl").exists()
        assert (tmp_path / "fake/gene/nodes.pl").read_text().count("gene(") >= 2
    elif writer_type == "metta":
        edges = (multi_aliases / "edges_alias_alias_of_protein.metta").read_text()
        assert "(protein P04637)" in edges


def test_alias_of_targets_cover_harmonizable_types(schema):
    from biocypher_metta.harmonization.schema_info import SchemaInfo

    schema_path, schema_dict = schema
    info = SchemaInfo.from_schema_file(schema_path, schema_dict)
    targets = set(schema_dict["alias_of"]["target"])
    assert set(info.ontology_term_labels()) | {"gene", "transcript", "protein"} <= targets
