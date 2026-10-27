# Entity Harmonization

Alternate names and cross-reference identifiers of genes, transcripts, proteins and ontology terms become `alias` nodes linked to the canonical node by `alias_of` edges. The same aliases are used at build time to rewrite edges that reference an entity by a secondary identifier, so they land on the canonical node instead of dangling.

Harmonization is opt-in per adapters-config entry. Without any `aliases:` key the build is unchanged.

Code: `biocypher_metta/harmonization/`, wired into `create_knowledge_graph.py`.

---

## Why

Before harmonization, alternate names were flat, untyped lists on the node (`gene.synonym`, `ontology term.synonym` / `alternative_ids`, `protein.accessions`). A gene's `synonym` mixed symbols, HGNC IDs, full names and designations; an ontology term's `synonym` merged exact and related synonyms. Nothing linked a name or an identifier back to a canonical entity, and edges that used another spelling of an identifier (`Ensembl:` vs `ENSEMBL:`, `UniProt:` or bare accession vs `UniProtKB:`, versioned IDs, ontology alt_ids, obsolete terms) did not connect to anything.

---

## Enabling aliases

Add `aliases:` to an entry with `nodes: True`:

```yaml
gencode_gene:
  adapter:
    module: biocypher_metta.adapters.gencode_gene_adapter
    cls: GencodeGeneAdapter
    args: {filepath: ensembl/gencode.gtf.gz, label: gene, taxon_id: 9606}
  outdir: ensembl/gene
  nodes: True
  edges: False
  aliases: true                      # every alias type the adapter has (broad/narrow synonyms excluded)
```

Narrow it per entry:

```yaml
  aliases:
    exclude_alias_types: [other_designation, full_name]
# or
  aliases:
    alias_types: [xref, secondary_accession, alternative_id, replaced_id]
```

`aliases:` on an entry with `nodes: False` is rejected. To keep one entry's edges out of endpoint rewriting, set `harmonize_edges: false` on that entry.

CLI switches (`create_knowledge_graph.py`):

| Flag | Effect |
|---|---|
| `--aliases` / `--no-aliases` | Honor or ignore every `aliases:` key (default: honor) |
| `--harmonize-edges` / `--no-harmonize-edges` | Rewrite edge endpoints through the alias registry (default: on). With `--no-harmonize-edges`, alias nodes are still written but no registry is built |

The hsa and dmel sample configs enable aliases on GENCODE genes and transcripts, Swiss-Prot, GO and most ontology node entries. ChEBI and EFO are left off: they are the largest alias sources and are best enabled deliberately.

### What changes for an alias-enabled adapter

- The canonical node is written as before, **minus its flat alias properties**: `synonym` (genes, ontology terms), `alternative_ids` (ontology terms), `accessions` (proteins). Those columns disappear from the output of that adapter.
- `alias` nodes and `alias_of` edges are written to `<outdir>/aliases/<adapter name>/` with the same writer.

Adapters that support aliases:

| Adapter | Node type | Alias types |
|---|---|---|
| `GencodeGeneAdapter` | gene | `approved_symbol`, `previous_symbol`, `alias_symbol` (HGNC, NCBI), `full_name`, `other_designation`, `xref` (HGNC, NCBIGene, HAVANA OTTHUMG, MGI) |
| `GencodeTranscriptAdapter` | transcript | `preferred_name` (transcript name), `xref` (HAVANA OTTHUMT) |
| `UniprotProteinAdapter` | protein | `secondary_accession`, `entry_name`, `approved_symbol`/`alias_symbol` (gene names), `other_designation` (ORF names), `recommended_name`, `alternative_name`, `short_name`, `xref` (Ensembl ENSP, RefSeq NP; isoform-qualified xrefs go to the isoform node) |
| `OntologyAdapter` and subclasses (GO, UBERON, CL, CLO, BTO, DO, HPO, HsapDv, SO, FB* …) | the adapter's ontology-term type | `preferred_name`, `exact_synonym`, `related_synonym`, `alternative_id`, `replaced_id` (obsolete terms via `IAO:0100001`, following chains); `broad_synonym`/`narrow_synonym` only when listed in `alias_types` |

All of these come from data the adapter already parses; nothing is downloaded or parsed a second time. Ontology adapters only alias terms of their own ontology (CL does not alias the UBERON terms it imports).

---

## Graph model

```
(alias {name: "p53", alias_kind: "name", entity_type: "gene", scope: "9606"})
    -[:alias_of {alias_type: ["alias_symbol"], alias_source: ["HGNC", "NCBI Gene"]}]->
(gene {id: "ENSEMBL:ENSG00000141510"})
```

**`alias` node** (`config/primer_schema_config.yaml`, `is_a: information content entity`):

| Property | Meaning |
|---|---|
| `name` | The alternate name, or the local part of an identifier (`11998` for `HGNC:11998`) |
| `namespace` | Identifier namespace (`HGNC`, `NCBIGene`, `UniProtKB`, `ENSEMBL`, `HAVANA`, `GO` …); absent for names |
| `normalized_name` | Case-folded `name`, for case-insensitive lookup |
| `alias_kind` | `identifier` or `name` |
| `entity_type` | `gene`, `transcript`, `protein` or `ontology_term` |
| `scope` | Taxon ID for genes/transcripts/proteins, ontology prefix for ontology terms |

The node ID is `ALIAS_<20 hex>`, a SHA-1 of `(entity_type, scope, kind, value)`. It contains no `:` or spaces, so every writer keeps the alias node and its edges in agreement with or without `--include-curie`. One alias string within a scope is **one** node: when several entities share it, the node has several `alias_of` edges. That out-degree is how ambiguity shows in the graph.

**`alias_of` edge**: `source: alias`, `target:` gene, transcript, protein and every ontology-term type. `alias_type` and `alias_source` are lists, because the same alias can be asserted in several ways and by several sources. `source`/`source_url` name the adapter's dataset when `--add-provenance` is on.

### Querying

Neo4j: find the genes a symbol may refer to:

```cypher
MATCH (a:alias {entity_type: 'gene', normalized_name: 'p53'})-[r:alias_of]->(g:gene)
RETURN g.id, g.gene_name, r.alias_type, r.alias_source
```

Neo4j: ambiguous gene symbols:

```cypher
MATCH (a:alias {entity_type: 'gene', alias_kind: 'name'})-[:alias_of]->(g:gene)
WITH a, collect(g.id) AS genes WHERE size(genes) > 1
RETURN a.name, genes
```

MeTTa (properties are separate facts):

```
(alias_of (alias ALIAS_452E1D296130B7AE6771) (gene ENSG00000141510))
(name (alias ALIAS_452E1D296130B7AE6771) TP53)
(alias_type (alias_of (alias ALIAS_452E1D296130B7AE6771) (gene ENSG00000141510)) approved_symbol)
```

```
!(match &self (, (name (alias $a) TP53) (alias_of (alias $a) (gene $g))) $g)
```

The MeTTa writer rewrites property values: without `--include-curie` it drops everything up to the first `:`, then turns spaces into `_` and drops characters outside `[A-Za-z0-9_:.-]`. Match multi-word names in the same mangled form; identifier aliases keep the namespace in a separate `namespace` fact for this reason.

---

## Edge endpoint harmonization

When aliases are enabled anywhere in the config, the build runs in two waves:

1. **Wave 1**: every work unit that writes only nodes. Alias-enabled adapters record each emitted node and its aliases in a per-adapter SQLite shard (`<output>/harmonization/shards/<adapter>.db`).
2. **Barrier**: shards are verified (see below) and merged into `<output>/harmonization/registry.db`: canonical IDs and identifier aliases per entity type. Names are not part of the registry.
3. **Wave 2**: every unit that writes edges. Each endpoint whose node type has canonical nodes in the registry is looked up by a normalized key (`biocypher_metta/harmonization/curie.py`: canonical prefixes, Ensembl/RefSeq versions stripped, OBO IRIs and `GO_0008150` forms, bare IDs inferred per entity type).

An entry with both `nodes: True` and `edges: True` is split into `<name>::nodes` (wave 1) and `<name>::edges` (wave 2), so its edges are harmonized too. Checkpoints track these unit names.

| Status | Meaning | Endpoint |
|---|---|---|
| `unchanged` | Already the emitted canonical ID | kept |
| `normalized` | Same identifier, different spelling (`Ensembl:` vs `ENSEMBL:`, `UniProtKB:P04637` vs `P04637`, version suffix) | rewritten to the emitted ID |
| `resolved` | An identifier alias naming exactly one entity at its strongest tier | rewritten |
| `ambiguous` | Several entities claim the key | kept, reported |
| `type_mismatch` | Only entities of a type the edge does not allow | kept, reported |
| `unresolved` | No canonical node or alias | kept, reported |
| `unmanaged` | Node type not harmonized in this run | kept |
| `skipped` | Edge is an identifier link (`has xref` and its subtypes, `alias_of`) | kept |

Identifier alias tiers: secondary accessions, ontology alt_ids and replaced terms (tier 1) outrank xrefs and UniProt entry names (tier 2). Canonical IDs always win over aliases.

In the default (no-CURIE) output, writers strip most prefixes, so many `normalized` rewrites do not change the written ID; with `--include-curie` they are what makes `UniProtKB:`/`UniProt:`/bare protein IDs and `Ensembl:`/`ENSEMBL:` gene IDs meet.

### Reports

| Path | Content |
|---|---|
| `harmonization/edges/<adapter>.tsv` | Every rewritten or kept endpoint of that adapter with counts (capped at 20,000 distinct rows) |
| `harmonization/unresolved_ids.tsv`, `ambiguous_ids.tsv`, `type_mismatch_ids.tsv` | Merged across adapters, most frequent first |
| `graph_info.json` → `harmonization` | Alias node/edge counts by target type and alias type, status totals overall and per adapter, registry size and ambiguity, report paths |

`harmonization/` is excluded from `graph_info.json`'s `data_size`.

### Shards, partial runs and resume

Each shard stores a fingerprint of what built it: adapter module/class, resolved constructor args, size and mtime of every input file named in them, the entry's `aliases:` selection, a digest of the schema entries it emitted, the version stamps of the HGNC / Entrez caches it read (gene adapter), and the content hash of the cached ontology file (ontology adapters). Before merging:

- Adapters run in this build: their shard must exist (it was just written).
- Adapters completed in an earlier, checkpointed run and resumed now: the shard must match the current config, else the run stops and asks for `--restart`.
- Adapters left out by `--include-adapters`: an existing shard is reused if it still matches; a stale one stops the run (include that adapter or pass `--no-harmonize-edges`); a missing one only warns and `registry_complete: false` is reported.

On resume, if the rebuilt registry differs from the one recorded when some wave-2 units completed, the run stops and asks for `--restart`.

---

## Limitations

- An alias asserted by two adapters (e.g. the three GO subontology adapters, or Swiss-Prot and TrEMBL) is written once per adapter. Neo4j `MERGE` and the NetworkX writer collapse the duplicates; MeTTa, Prolog, Parquet and KGX output keep identical duplicate rows.
- `data_source_schemas/` are generated from adapter code and do not list `alias`/`alias_of`, and still list `synonym` for adapters whose entries enable aliases.
- kg-service has no alias lookup endpoint yet; query the graph directly.
- Symbol-based adapters (TFBS, EPD, ABC, …) resolve gene symbols through `HGNCProcessor.get_ensembl_id`, not the alias registry. That lookup now falls back from approved to unique previous to unique alias symbols (case-insensitively last).
