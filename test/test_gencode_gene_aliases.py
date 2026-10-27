"""GENCODE gene synonym lookup by HGNC ID.

NCBI gene_info dbXrefs read 'HGNC:HGNC:<n>', so alias dicts are keyed
'HGNC:<n>'. The fallback used to strip the prefix before looking up, which
never matched; genes known to NCBI only by HGNC ID got no synonyms.
"""

import gzip

import biocypher_metta.adapters.gencode_gene_adapter as gencode_module
from biocypher_metta.adapters.gencode_gene_adapter import GencodeGeneAdapter

_GTF = (
    'chr19\tHAVANA\tgene\t58345178\t58353492\t.\t-\t.\tgene_id "ENSG00000121410.13"; '
    'gene_type "protein_coding"; gene_name "A1BG"; level 2; hgnc_id "HGNC:5"; '
    'havana_gene "OTTHUMG00000183507.1";\n'
)

_GENE_INFO_HEADER = "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\tdbXrefs\tchromosome\tmap_location\tdescription\ttype_of_gene\tSymbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\tNomenclature_status\tOther_designations\tModification_date\tFeature_type\n"
# No 'Ensembl:' dbXref, so the gene is reachable only through its HGNC ID.
_GENE_INFO_ROW = "9606\t1\tA1BG\t-\tA1B|ABG\tMIM:138670|HGNC:HGNC:5\t19\t19q13.43\talpha-1-B glycoprotein\tprotein-coding\tA1BG\talpha-1-B glycoprotein\tO\talpha-1B-glycoprotein\t20240101\t-\n"


class _StubHGNC:
    def load_or_update(self):
        return {}

    def process_identifier(self, identifier):
        return {"status": "current", "original": identifier, "current": identifier}


def test_gene_known_only_by_hgnc_id_gets_synonyms(tmp_path, monkeypatch):
    monkeypatch.setattr(gencode_module, "HGNCProcessor", _StubHGNC)
    gtf = tmp_path / "gencode.v49.test.gtf.gz"
    gene_info = tmp_path / "Homo_sapiens.gene_info.gz"
    with gzip.open(gtf, "wt") as f:
        f.write(_GTF)
    with gzip.open(gene_info, "wt") as f:
        f.write(_GENE_INFO_HEADER + _GENE_INFO_ROW)

    adapter = GencodeGeneAdapter(
        write_properties=True, add_provenance=False, taxon_id=9606,
        filepath=str(gtf), label="gene", gene_alias_file_path=str(gene_info),
    )
    [(node_id, label, props)] = list(adapter.get_nodes())

    assert node_id == "ENSEMBL:ENSG00000121410"
    assert label == "gene"
    assert {"A1BG", "A1B", "ABG", "HGNC:5"} <= set(props["synonym"])
