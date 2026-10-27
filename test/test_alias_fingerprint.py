"""Shard fingerprints: a shard is only merged while its inputs are unchanged."""

import os

import pytest
import yaml

from biocypher_metta.harmonization import fingerprint as fp
from biocypher_metta.harmonization.aliases import AliasSelection
from biocypher_metta.harmonization.pipeline import HarmonizationContext, compute_fingerprint
from biocypher_metta.harmonization.schema_info import SchemaInfo
from biocypher_metta.harmonization.shard import AliasShard


@pytest.fixture
def schema_info(tmp_path):
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump({
        "gene": {"represented_as": "node", "input_label": "gene", "properties": {"gene_name": {"type": "str"}}},
        "protein": {"represented_as": "node", "input_label": "protein"},
    }))
    return SchemaInfo.from_schema_file(path, {})


def _entry(path, **extra):
    return {
        "adapter": {"module": "harmonization_fakes", "cls": "FakeGeneAdapter",
                    "args": {"filepath": str(path), "label": "gene", "write_properties": True}},
        "outdir": "g", "nodes": True, "edges": False, "aliases": True, **extra,
    }


def _digest(entry, schema_info, selection=None, labels=("gene",)):
    return fp.digest(compute_fingerprint("g", entry, selection or AliasSelection(), schema_info, labels))


def test_fingerprint_tracks_inputs(tmp_path, schema_info):
    data = tmp_path / "genes.tsv"
    data.write_text("a")
    entry = _entry(data)
    base = _digest(entry, schema_info)

    assert _digest(entry, schema_info) == base                                  # stable
    entry["adapter"]["args"]["write_properties"] = False
    assert _digest(entry, schema_info) == base                                  # runtime-injected arg ignored

    data.write_text("ab")                                                       # size
    assert _digest(entry, schema_info) != base
    base = _digest(entry, schema_info)
    os.utime(data, ns=(1, 1))                                                   # mtime
    assert _digest(entry, schema_info) != base
    base = _digest(entry, schema_info)

    assert _digest(entry, schema_info, AliasSelection(exclude_alias_types=["full_name"])) != base
    assert _digest(entry, schema_info, labels=("gene", "protein")) != base


def test_fingerprint_tracks_schema_entries(tmp_path, schema_info):
    data = tmp_path / "genes.tsv"
    data.write_text("a")
    entry = _entry(data)
    base = _digest(entry, schema_info)

    path = tmp_path / "schema2.yaml"
    path.write_text(yaml.safe_dump({
        "gene": {"represented_as": "node", "input_label": "gene", "properties": {"gene_name": {"type": "str"}, "x": {"type": "int"}}},
        "protein": {"represented_as": "node", "input_label": "protein"},
    }))
    assert _digest(entry, SchemaInfo.from_schema_file(path, {})) != base

    # A schema change to a label the adapter does not emit is irrelevant.
    path.write_text(yaml.safe_dump({
        "gene": {"represented_as": "node", "input_label": "gene", "properties": {"gene_name": {"type": "str"}}},
        "protein": {"represented_as": "node", "input_label": "protein", "properties": {"y": {"type": "str"}}},
    }))
    assert _digest(entry, SchemaInfo.from_schema_file(path, {})) == base


def test_fingerprint_tracks_processor_cache_versions(tmp_path, schema_info, monkeypatch):
    import harmonization_fakes

    stamp = {"value": "2026-01-01"}
    monkeypatch.setattr(harmonization_fakes.FakeGeneAdapter, "alias_fingerprint_deps",
                        classmethod(lambda cls, args: {"hgnc": stamp["value"]}), raising=False)
    data = tmp_path / "genes.tsv"
    data.write_text("a")
    entry = _entry(data)
    base = _digest(entry, schema_info)
    stamp["value"] = "2026-02-01"
    assert _digest(entry, schema_info) != base


def test_diff_names_changed_fields(tmp_path, schema_info):
    data = tmp_path / "genes.tsv"
    data.write_text("a")
    old = compute_fingerprint("g", _entry(data), AliasSelection(), schema_info, ["gene"])
    data.write_text("abc")
    new = compute_fingerprint("g", _entry(data), AliasSelection(exclude_alias_types=["xref"]), schema_info, ["gene"])
    assert fp.diff(old, new) == ["aliases", "files"]


def test_missing_out_of_run_shard_only_warns(tmp_path, schema_info):
    data = tmp_path / "genes.tsv"
    data.write_text("a")
    present, absent = _entry(data), _entry(data)
    context = HarmonizationContext(tmp_path, schema_info, {}, {"present": present, "absent": absent})

    shard = AliasShard(context.shard_dir, "present", AliasSelection(), schema_info)
    shard.record_node("ENSEMBL:ENSG00000141510", "gene", {}, [])
    shard.finalize(compute_fingerprint("present", present, AliasSelection(), schema_info, sorted(shard.labels)))

    stats = context.build_registry(executed_now=set(), resumed=set())
    assert stats["registry_complete"] is False
    assert stats["missing_shards"] == ["absent"]
    assert stats["canonical_ids"] == 1


def test_fingerprint_ignores_directory_churn(tmp_path, schema_info):
    data = tmp_path / "genes.tsv"
    data.write_text("a")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    entry = _entry(data)
    entry["adapter"]["args"]["cache_dir"] = str(cache_dir)
    base = _digest(entry, schema_info)
    (cache_dir / "other_ontology.owl").write_text("x")      # unrelated file lands in the shared dir
    assert _digest(entry, schema_info) == base


def test_ontology_fingerprint_tracks_cached_ontology_hash(tmp_path):
    import json as _json
    from biocypher_metta.adapters.ontologies_adapter import OntologyAdapter

    meta = tmp_path / "go_meta.json"
    meta.write_text(_json.dumps({"hash": "aaa", "version": "1"}))
    args = {"ontology": "go", "cache_dir": str(tmp_path)}
    assert OntologyAdapter.alias_fingerprint_deps(args) == {"ontology_cache": "aaa"}
    meta.write_text(_json.dumps({"hash": "bbb", "version": "1"}))
    assert OntologyAdapter.alias_fingerprint_deps(args) == {"ontology_cache": "bbb"}
