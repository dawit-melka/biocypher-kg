"""HGNC symbol resolution.

Guards the alias-splitting regression (HGNC joins multi-valued columns with
", ", which the processor used to split on "|", leaving keys such as
'NCRNA00181, A1BGAS, A1BG-AS'), last-write-wins resolution of shared aliases,
and the missing alias fallback in get_ensembl_id. All tests are network-free.
"""

import gzip
import json
import pickle

import pytest

from biocypher_metta.processors.hgnc_processor import HGNCProcessor

_HGNC_TSV = "\n".join([
    "HGNC ID\tApproved symbol\tApproved name\tPrevious symbols\tAlias symbols\tNCBI Gene ID\tEnsembl gene ID",
    "HGNC:5\tA1BG\talpha-1-B glycoprotein\t\t\t1\tENSG00000121410",
    "HGNC:37133\tA1BG-AS1\tA1BG antisense RNA 1\tNCRNA00181, A1BGAS, A1BG-AS\tFLJ23569\t503538\tENSG00000268895",
    "HGNC:11998\tTP53\ttumor protein p53\t\tp53, LFS1\t7157\tENSG00000141510",
    # 'ASP' is an alias of two genes; 'OLD1' is a previous symbol of GENEA and an alias of GENEB.
    "HGNC:1\tGENEA\tgene a\tOLD1\tASP\t11\tENSG00000000001",
    "HGNC:2\tGENEB\tgene b\t\tASP, OLD1\t12\tENSG00000000002",
    "HGNC:3\tNOENS\tno ensembl gene\t\tNOENS-ALIAS\t13\t",
]) + "\n"


def _processor(tmp_path):
    return HGNCProcessor(cache_dir=str(tmp_path / "hgnc"), update_interval_hours=48)


@pytest.fixture
def hgnc(tmp_path):
    p = _processor(tmp_path)
    p.mapping = p.process_data(_HGNC_TSV)
    return p


def test_multi_valued_columns_are_split(hgnc):
    aliases = hgnc.mapping["symbol_aliases"]
    assert not any(", " in key for key in aliases)
    for old in ("NCRNA00181", "A1BGAS", "A1BG-AS", "FLJ23569"):
        assert aliases[old] == "A1BG-AS1"
    assert hgnc.mapping["symbol_to_previous"]["A1BG-AS1"] == ["NCRNA00181", "A1BGAS", "A1BG-AS"]
    assert hgnc.mapping["symbol_to_alias"]["TP53"] == ["p53", "LFS1"]


def test_ambiguous_alias_is_not_resolved(hgnc):
    assert hgnc.mapping["alias_to_symbols"]["ASP"] == ["GENEA", "GENEB"]
    assert "ASP" not in hgnc.mapping["symbol_aliases"]
    assert hgnc.resolve_symbol("ASP") is None
    assert hgnc.get_ensembl_id("ASP") is None
    assert hgnc.process_identifier("ASP")["status"] == "unknown"


def test_previous_symbol_beats_alias(hgnc):
    # OLD1 is GENEA's previous symbol and GENEB's alias: previous wins.
    assert hgnc.resolve_symbol("OLD1") == "GENEA"
    assert hgnc.get_symbol_candidates("OLD1") == {"approved": [], "previous": ["GENEA"], "alias": ["GENEB"]}


def test_get_ensembl_id_falls_back_through_aliases(hgnc):
    assert hgnc.get_ensembl_id("TP53") == "ENSG00000141510"
    assert hgnc.get_ensembl_id("LFS1") == "ENSG00000141510"
    assert hgnc.get_ensembl_id("A1BGAS") == "ENSG00000268895"
    assert hgnc.get_ensembl_id("HGNC:11998") == "ENSG00000141510"
    # Approved symbol without an Ensembl ID must not fall through to an alias.
    assert hgnc.get_ensembl_id("NOENS") is None
    assert hgnc.get_ensembl_id("UNKNOWN") is None


def test_case_insensitive_fallback_only_after_exact(hgnc):
    assert hgnc.resolve_symbol("P53") == "TP53"   # HGNC lists the alias as 'p53'
    assert hgnc.resolve_symbol("tp53") == "TP53"
    assert hgnc.resolve_symbol("asp") is None     # still ambiguous case-insensitively


def test_process_identifier_statuses(hgnc):
    assert hgnc.process_identifier("TP53") == {"status": "current", "original": "TP53", "current": "TP53"}
    assert hgnc.process_identifier("A1BGAS")["current"] == "A1BG-AS1"
    assert hgnc.process_identifier("A1BGAS")["status"] == "updated"
    assert hgnc.process_identifier("ENSG00000141510.18")["status"] == "ensembl_with_symbol"


def test_symbol_record(hgnc):
    assert hgnc.get_symbol_record("TP53") == {
        "symbol": "TP53", "hgnc_id": "HGNC:11998", "name": "tumor protein p53", "entrez_id": "7157",
        "previous_symbols": [], "alias_symbols": ["p53", "LFS1"],
    }


def test_legacy_cache_is_migrated_offline(tmp_path, monkeypatch):
    legacy = {
        "current_symbols": {"A1BG-AS1": "A1BG-AS1", "TP53": "TP53"},
        "symbol_aliases": {"NCRNA00181, A1BGAS, A1BG-AS": "A1BG-AS1", "FLJ23569": "A1BG-AS1"},
        "ensembl_to_symbol": {"ENSG00000268895": "A1BG-AS1"},
        "symbol_to_ensembl": {"A1BG-AS1": "ENSG00000268895", "TP53": "ENSG00000141510"},
        "hgnc_id_to_symbol": {}, "hgnc_id_to_ensembl": {},
    }
    cache = tmp_path / "hgnc"
    cache.mkdir()
    with gzip.open(cache / "hgnc_mapping.pkl", "wb") as f:
        pickle.dump(legacy, f)
    (cache / "hgnc_version.json").write_text(json.dumps({"timestamp": "2099-01-01T00:00:00", "entries": 5}))

    def offline():
        raise ConnectionError("no network in tests")

    p = _processor(tmp_path)
    monkeypatch.setattr(p, "fetch_data", offline)
    p.load_or_update()

    assert p.mapping["symbol_aliases"]["A1BGAS"] == "A1BG-AS1"
    assert p.get_ensembl_id("NCRNA00181") == "ENSG00000268895"
    assert "NCRNA00181, A1BGAS, A1BG-AS" not in p.mapping["symbol_aliases"]
