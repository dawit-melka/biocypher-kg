"""One CURIE normalizer for alias values, canonical node IDs and edge endpoints.

Adapters spell the same namespace several ways (``ENSEMBL:``/``Ensembl:``,
``UniProtKB:``/``UniProt:``/bare accession, ``HGNC:HGNC:5``, OBO IRIs, versioned
Ensembl IDs). ``lookup_key`` maps every spelling of one identifier onto a single
key; the registry stores the emitted canonical ID verbatim next to that key.
"""

import re
from typing import NamedTuple, Optional

# Lower-cased spelling -> canonical prefix.
_PREFIX_SYNONYMS = {
    "ensembl": "ENSEMBL",
    "ensembl_gene": "ENSEMBL",
    "ensembl_transcript": "ENSEMBL",
    "ensembl_protein": "ENSEMBL",
    "uniprot": "UniProtKB",
    "uniprotkb": "UniProtKB",
    "uniprot/swiss-prot": "UniProtKB",
    "swissprot": "UniProtKB",
    "trembl": "UniProtKB",
    "ncbigene": "NCBIGene",
    "ncbi_gene": "NCBIGene",
    "geneid": "NCBIGene",
    "entrez": "NCBIGene",
    "entrezgene": "NCBIGene",
    "hgnc": "HGNC",
    "flybase": "FlyBase",
    "fb": "FlyBase",
    "wormbase": "WormBase",
    "wb": "WormBase",
    "mgi": "MGI",
    "rgd": "RGD",
    "refseq": "RefSeq",
    "havana": "HAVANA",
    "vega": "HAVANA",
}

_ENSEMBL_ID = re.compile(r"^(ENS[A-Z]*[EGTP]\d{11})(?:\.\d+)?(_PAR_Y)?$", re.IGNORECASE)
_HAVANA_ID = re.compile(r"^(OTT[A-Z]{3,4}[GTP]\d{11})(?:\.\d+)?$", re.IGNORECASE)
_REFSEQ_ID = re.compile(r"^([NXYW][MRP]_\d+)(?:\.\d+)?$", re.IGNORECASE)
_UNIPROT_ID = re.compile(
    r"^([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})(-\d+)?$",
    re.IGNORECASE,
)
_FLYBASE_ID = re.compile(r"^FB[a-z]{2}\d{7}$", re.IGNORECASE)
_WORMBASE_ID = re.compile(r"^WBGene\d{8}$", re.IGNORECASE)
_OBO_LOCAL = re.compile(r"^([A-Za-z][A-Za-z0-9.]*)_([A-Za-z0-9][A-Za-z0-9_.-]*)$")


class Curie(NamedTuple):
    prefix: str
    local: str

    def __str__(self):
        return f"{self.prefix}:{self.local}"


def canonical_prefix(prefix: str) -> str:
    return _PREFIX_SYNONYMS.get(prefix.strip().lower(), prefix.strip())


def _infer_prefix(local: str, entity_class: Optional[str]) -> Optional[str]:
    if _ENSEMBL_ID.match(local):
        return "ENSEMBL"
    if _HAVANA_ID.match(local):
        return "HAVANA"
    if _FLYBASE_ID.match(local):
        return "FlyBase"
    if _WORMBASE_ID.match(local):
        return "WormBase"
    if _REFSEQ_ID.match(local) and entity_class in (None, "transcript", "protein"):
        return "RefSeq"
    if entity_class == "protein" and _UNIPROT_ID.match(local):
        return "UniProtKB"
    return None


def _normalize_local(prefix: str, local: str) -> str:
    local = local.strip()
    # 'HGNC:HGNC:5' style double prefixes (NCBI dbXrefs).
    while local.lower().startswith(prefix.lower() + ":"):
        local = local[len(prefix) + 1:]
    if prefix == "ENSEMBL":
        m = _ENSEMBL_ID.match(local)
        if m:
            return m.group(1).upper() + (m.group(2) or "")
    elif prefix == "HAVANA":
        m = _HAVANA_ID.match(local)
        if m:
            return m.group(1).upper()
    elif prefix == "RefSeq":
        m = _REFSEQ_ID.match(local)
        if m:
            return m.group(1).upper()
    elif prefix == "UniProtKB":
        return local.upper()
    return local


def _from_iri(raw: str) -> Optional[str]:
    tail = re.split(r"[/#]", raw.rstrip("/#"))[-1]
    return tail or None


def normalize(raw, entity_class: Optional[str] = None) -> Optional[Curie]:
    """Parse any supported spelling of an identifier into a canonical ``Curie``.

    Returns None when the value carries no recognisable namespace (a free-text
    name, or a bare ID whose namespace cannot be inferred for this entity class).
    """
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None

    if value.startswith(("http://", "https://")):
        tail = _from_iri(value)
        if tail is None:
            return None
        if ":" not in tail:
            m = _OBO_LOCAL.match(tail)
            if not m:
                return None
            return Curie(canonical_prefix(m.group(1)), m.group(2))
        value = tail

    if ":" in value:
        prefix, local = value.split(":", 1)
        if prefix and local and " " not in prefix:
            prefix = canonical_prefix(prefix)
            return Curie(prefix, _normalize_local(prefix, local))
        return None

    prefix = _infer_prefix(value, entity_class)
    if prefix:
        return Curie(prefix, _normalize_local(prefix, value))

    if entity_class == "ontology_term":
        m = _OBO_LOCAL.match(value)
        if m:
            return Curie(canonical_prefix(m.group(1)), m.group(2))
    return None


def lookup_key(raw, entity_class: Optional[str] = None) -> Optional[str]:
    """Case-insensitive registry key for an identifier, or None if unparseable.

    IDs in this KG are effectively case-insensitive: writers upper- or
    lower-case them on output.
    """
    curie = raw if isinstance(raw, Curie) else normalize(raw, entity_class)
    if curie is None:
        return None
    return f"{curie.prefix}:{curie.local}".upper()
