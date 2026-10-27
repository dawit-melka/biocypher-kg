"""Entity harmonization through process_adapters: waves, work units, the edge
harmonizer, sequential/parallel equivalence, checkpoint resume and shard
fingerprint checks. Uses fake adapters (test/harmonization_fakes.py) and the
real merged hsa schema with the MeTTa writer; network-free.
"""

import copy
import json
from pathlib import Path

import pytest

import create_knowledge_graph as ck
from biocypher_metta.harmonization.pipeline import HarmonizationError, plan_waves
from checkpoint_manager import CheckpointManager


@pytest.fixture(scope="module")
def schema():
    merged = ck.merge_schemas("config/primer_schema_config.yaml", "config/hsa/hsa_schema_config.yaml")
    try:
        yield merged, ck.preprocess_schema(merged)
    finally:
        ck.delete_temp_schema(merged)


def _config(fail_marker=None, aliases=True):
    gene = {
        "adapter": {"module": "harmonization_fakes", "cls": "FakeGeneAdapter", "args": {"label": "gene"}},
        "outdir": "fake/gene",
        "nodes": True,
        "edges": True,       # split into fake_gene::nodes (wave 1) + fake_gene::edges (wave 2)
    }
    if aliases is not None:
        gene["aliases"] = aliases
    return {
        "fake_gene": gene,
        "fake_edges": {      # edge-only entry sharing the gene adapter's outdir
            "adapter": {"module": "harmonization_fakes", "cls": "FakeEdgeAdapter",
                        "args": {"label": "coexpressed_with", "fail_marker": fail_marker}},
            "outdir": "fake/gene",
            "nodes": False,
            "edges": True,
        },
    }


def _run(schema, out, config, max_workers=1, checkpoint=None, harmonize_edges=True):
    schema_path, schema_dict = schema
    harmonization = ck._setup_harmonization(config, config, schema_path, schema_dict, out, True, harmonize_edges)
    writer = ck.get_writer("metta", out, schema_path) if max_workers == 1 else None
    writer_kwargs = {"writer_type": "metta", "output_dir": out, "schema_config_path": schema_path,
                     "include_curie": False, "import_root": None}
    result = ck.process_adapters(
        config, {}, {}, writer, True, True, schema_dict,
        checkpoint_manager=checkpoint, skip_preflight=True,
        writer_kwargs=writer_kwargs, max_workers=max_workers, harmonization=harmonization,
    )
    return result, harmonization


def _read_outputs(out: Path):
    return {
        str(p.relative_to(out)): p.read_text()
        for p in sorted(out.rglob("*.metta"))
    }


def test_plan_waves_splits_node_and_edge_work():
    wave1, wave2 = plan_waves(_config())
    assert list(wave1) == ["fake_gene::nodes"]
    assert list(wave2) == ["fake_gene::edges", "fake_edges"]
    assert wave1["fake_gene::nodes"]["edges"] is False
    assert wave2["fake_gene::edges"]["nodes"] is False


def test_sequential_pipeline_rewrites_and_reports(schema, tmp_path):
    (nodes_count, nodes_props, edges_count, *_), harmonization = _run(schema, tmp_path, _config())

    assert nodes_count["gene"] == 2
    assert nodes_count["alias"] > 0
    assert "synonym" not in nodes_props["gene"]           # legacy flat list dropped
    assert {"name", "alias_kind", "entity_type", "scope"} <= nodes_props["alias"]
    assert edges_count["alias_of|alias|gene"] > 0

    edges = (tmp_path / "fake/gene/edges_gene_coexpressed_with_gene.metta").read_text()
    # fake_gene's own HGNC-ID edge and fake_edges' alias/spelling variants were rewritten.
    assert "(coexpressed_with (gene ENSG00000141510) (gene ENSG00000135679))" in edges
    assert "HGNC" not in edges
    # Unresolvable endpoints are kept as-is.
    assert "ENSG00000000001" in edges and "P53" in edges.upper()

    summary = harmonization.summary()
    statuses = summary["edge_harmonization"]["statuses"]
    assert statuses["resolved"] == 3        # two in fake_gene's edge, one in fake_edges
    assert statuses["normalized"] == 1
    assert statuses["unresolved"] == 2      # ENSG00000000001 and the name 'p53'
    assert summary["registry"]["registry_complete"] is True

    alias_nodes = (tmp_path / "fake/gene/aliases/fake_gene/nodes_alias.metta").read_text()
    assert "(alias ALIAS_" in alias_nodes
    unresolved = (tmp_path / "harmonization/unresolved_ids.tsv").read_text()
    assert "ENSEMBL:ENSG00000000001" in unresolved


def test_parallel_matches_sequential(schema, tmp_path):
    _run(schema, tmp_path / "seq", _config())
    _run(schema, tmp_path / "par", _config(), max_workers=2)
    seq, par = _read_outputs(tmp_path / "seq"), _read_outputs(tmp_path / "par")
    assert seq.keys() == par.keys()
    for name in seq:
        assert sorted(seq[name].splitlines()) == sorted(par[name].splitlines()), name


def test_aliases_off_keeps_legacy_output(schema, tmp_path):
    (_, nodes_props, edges_count, *_), harmonization = _run(schema, tmp_path, _config(aliases=None))
    assert harmonization is None
    assert "synonym" in nodes_props["gene"]
    assert not (tmp_path / "harmonization").exists()
    edges = (tmp_path / "fake/gene/edges_gene_coexpressed_with_gene.metta").read_text()
    assert "11998" in edges     # untouched HGNC endpoint


def test_no_harmonize_edges_writes_aliases_only(schema, tmp_path):
    _, harmonization = _run(schema, tmp_path, _config(), harmonize_edges=False)
    assert (tmp_path / "fake/gene/aliases/fake_gene/nodes_alias.metta").exists()
    assert not (tmp_path / "harmonization/registry.db").exists()
    assert harmonization.summary()["edge_harmonization"]["statuses"] == {}


def _checkpoint(out):
    return CheckpointManager(out, pipeline_id="test::harmonization")


def test_resume_after_wave2_failure(schema, tmp_path):
    marker = tmp_path / "fail"
    marker.touch()
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="fake edge adapter failure"):
        _run(schema, out, _config(fail_marker=str(marker)), checkpoint=_checkpoint(out))

    state = json.loads((out / "kg_checkpoint.json").read_text())
    assert "fake_gene::nodes" in state["completed_adapters"]
    assert "fake_edges" not in state["completed_adapters"]
    assert "gencode_gene" not in state["extra"]["harmonization"]["aliases"]
    assert "fake_gene" in state["extra"]["harmonization"]["aliases"]

    marker.unlink()
    ckpt = _checkpoint(out)
    assert ckpt.load()
    (nodes_count, _, _, *_), harmonization = _run(schema, out, _config(fail_marker=str(marker)), checkpoint=ckpt)
    assert nodes_count["gene"] == 2       # restored, not re-counted
    statuses = harmonization.summary()["edge_harmonization"]["statuses"]
    assert statuses["resolved"] == 3


def test_resume_fails_when_shard_config_changed(schema, tmp_path):
    marker = tmp_path / "fail"
    marker.touch()
    out = tmp_path / "out"
    with pytest.raises(RuntimeError):
        _run(schema, out, _config(fail_marker=str(marker)), checkpoint=_checkpoint(out))

    marker.unlink()
    ckpt = _checkpoint(out)
    assert ckpt.load()
    changed = _config(fail_marker=str(marker), aliases={"alias_types": ["xref"]})
    with pytest.raises(HarmonizationError, match="--restart"):
        _run(schema, out, changed, checkpoint=ckpt)


def test_partial_run_reuses_and_verifies_shards(schema, tmp_path):
    full = _config()
    _run(schema, tmp_path, copy.deepcopy(full))

    # Edge-only rerun: the gene adapter is not in this run, its shard is reused.
    schema_path, schema_dict = schema
    only_edges = {"fake_edges": copy.deepcopy(full["fake_edges"])}
    harmonization = ck._setup_harmonization(full, only_edges, schema_path, schema_dict, tmp_path, True, True)
    writer = ck.get_writer("metta", tmp_path, schema_path)
    ck.process_adapters(only_edges, {}, {}, writer, True, True, schema_dict, skip_preflight=True,
                        harmonization=harmonization)
    assert harmonization.summary()["edge_harmonization"]["statuses"]["resolved"] == 1

    # The gene adapter's config changed since its shard was written: refuse to resolve against it.
    stale = copy.deepcopy(full)
    stale["fake_gene"]["adapter"]["args"]["taxon_id"] = 10090
    harmonization = ck._setup_harmonization(stale, only_edges, schema_path, schema_dict, tmp_path, True, True)
    writer = ck.get_writer("metta", tmp_path, schema_path)
    with pytest.raises(HarmonizationError, match="Stale alias shard"):
        ck.process_adapters(only_edges, {}, {}, writer, True, True, schema_dict, skip_preflight=True,
                            harmonization=harmonization)


def test_invalid_alias_entries_rejected(schema, tmp_path):
    schema_path, schema_dict = schema
    bad = _config()
    bad["fake_edges"]["aliases"] = True     # edge-only entry
    with pytest.raises(ck.typer.Exit):
        ck._setup_harmonization(bad, bad, schema_path, schema_dict, tmp_path, True, True)


def test_identifier_link_edges_are_not_rewritten(schema, tmp_path):
    _, harmonization = _run(schema, tmp_path, _config())
    assert {"has_xref", "protein_has_xref_gene", "alias_of"} <= harmonization.schema_info.identifier_link_labels

    harmonizer = harmonization.edge_harmonizer("xref_test")
    # The xref target is TP53's HGNC alias; resolving it would point the xref at the gene node itself.
    edge = (("protein", "P04637"), ("gene", "HGNC:11998"), "protein_has_xref_gene", {})
    assert list(harmonizer.wrap([edge])) == [edge]
    assert harmonizer.summary()["statuses"] == {"skipped": 2}


def test_alias_entry_on_unsupported_adapter_rejected_at_setup(schema, tmp_path):
    schema_path, schema_dict = schema
    config = _config()
    config["fake_edges"]["nodes"] = True
    config["fake_edges"]["aliases"] = True      # FakeEdgeAdapter does not support aliases
    with pytest.raises(ck.typer.Exit):
        ck._setup_harmonization(config, config, schema_path, schema_dict, tmp_path, True, True)


def test_failed_node_write_leaves_no_shard(schema, tmp_path, monkeypatch):
    import harmonization_fakes

    def broken_nodes(self):
        yield "ENSEMBL:ENSG00000141510", "gene", {}
        raise RuntimeError("adapter crashed mid-stream")

    monkeypatch.setattr(harmonization_fakes.FakeGeneAdapter, "get_nodes", broken_nodes)
    with pytest.raises(RuntimeError, match="mid-stream"):
        _run(schema, tmp_path, _config())
    shard_dir = tmp_path / "harmonization/shards"
    assert not list(shard_dir.glob("*.db")) and not list(shard_dir.glob("*.tmp"))
