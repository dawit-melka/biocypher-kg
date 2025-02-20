// Define schema for biological database
// Define all property keys - common fields
schema.propertyKey("id").asText().ifNotExist().create();
schema.propertyKey("chr").asText().ifNotExist().create();
schema.propertyKey("start").asInt().ifNotExist().create();
schema.propertyKey("end").asInt().ifNotExist().create();
schema.propertyKey("term_name").asText().ifNotExist().create();
schema.propertyKey("description").asText().ifNotExist().create();
schema.propertyKey("synonyms").asText().ifNotExist().create();
schema.propertyKey("gene_name").asText().ifNotExist().create();
schema.propertyKey("biological_context").asText().ifNotExist().create();
schema.propertyKey("data_source").asText().ifNotExist().create();

// Special property keys for specific node types
schema.propertyKey("gene_type").asText().ifNotExist().create();
schema.propertyKey("protein_name").asText().ifNotExist().create();
schema.propertyKey("accessions").asText().ifNotExist().create();
schema.propertyKey("transcript_name").asText().ifNotExist().create();
schema.propertyKey("transcript_id").asText().ifNotExist().create();
schema.propertyKey("transcript_type").asText().ifNotExist().create();
schema.propertyKey("gene_id").asText().ifNotExist().create();
schema.propertyKey("exon_number").asInt().ifNotExist().create();
schema.propertyKey("exon_id").asText().ifNotExist().create();
schema.propertyKey("ref").asText().ifNotExist().create();
schema.propertyKey("alt").asText().ifNotExist().create();
schema.propertyKey("caf_ref").asText().ifNotExist().create();
schema.propertyKey("caf_alt").asText().ifNotExist().create();
schema.propertyKey("variant_accession").asText().ifNotExist().create();
schema.propertyKey("variant_type").asText().ifNotExist().create();
schema.propertyKey("evidence").asText().ifNotExist().create();
schema.propertyKey("rsid").asText().ifNotExist().create();
schema.propertyKey("raw_cadd_score").asFloat().ifNotExist().create();
schema.propertyKey("phred_score").asFloat().ifNotExist().create();
schema.propertyKey("enhancer_id").asText().ifNotExist().create();
schema.propertyKey("se_id").asText().ifNotExist().create();
schema.propertyKey("rna_type").asText().ifNotExist().create();
schema.propertyKey("pathway_name").asText().ifNotExist().create();
schema.propertyKey("tf_name").asText().ifNotExist().create();
schema.propertyKey("pwm_A").asText().ifNotExist().create();
schema.propertyKey("pwm_C").asText().ifNotExist().create();
schema.propertyKey("pwm_G").asText().ifNotExist().create();
schema.propertyKey("pwm_T").asText().ifNotExist().create();
schema.propertyKey("length").asText().ifNotExist().create();
schema.propertyKey("genes").asText().ifNotExist().create();


// Define additional property keys needed for edges
schema.propertyKey("score").asFloat().ifNotExist().create();
schema.propertyKey("p_value").asFloat().ifNotExist().create();
schema.propertyKey("rel_type").asText().ifNotExist().create();
schema.propertyKey("qualifier").asText().ifNotExist().create();
schema.propertyKey("db_reference").asText().ifNotExist().create();
schema.propertyKey("slope").asFloat().ifNotExist().create();
schema.propertyKey("maf").asFloat().ifNotExist().create();
schema.propertyKey("q_value").asFloat().ifNotExist().create();
schema.propertyKey("pos").asInt().ifNotExist().create();
schema.propertyKey("distance").asInt().ifNotExist().create();
schema.propertyKey("ancestry").asText().ifNotExist().create();
schema.propertyKey("r2").asFloat().ifNotExist().create();
schema.propertyKey("d_prime").asFloat().ifNotExist().create();
schema.propertyKey("effect").asText().ifNotExist().create();
schema.propertyKey("detection_method").asText().ifNotExist().create();
schema.propertyKey("databases").asText().ifNotExist().create();
schema.propertyKey("evidence_type").asText().ifNotExist().create();
schema.propertyKey("state").asText().ifNotExist().create();
schema.propertyKey("modification").asText().ifNotExist().create();



// Define vertex labels

// schema.vertexLabel("ontology_term")
//       .properties("id", "term_name", "description", "synonyms")
//       .primaryKeys("id")
//       .nullableKeys("description", "synonyms")
//       .ifNotExist()
//       .create();

schema.vertexLabel("gene")
      .properties("id", "chr", "start", "end", "gene_name", "gene_type", "synonyms")
      .primaryKeys("id")
      .nullableKeys("gene_type", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("protein")
      .properties("id", "chr", "start", "end", "accessions", "protein_name", "synonyms")
      .primaryKeys("id")
      .nullableKeys("accessions", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("transcript")
      .properties("id", "chr", "start", "end", "gene_name", "transcript_name", "transcript_id", "transcript_type")
      .primaryKeys("id")
      .nullableKeys("transcript_type")
      .ifNotExist()
      .create();

schema.vertexLabel("exon")
      .properties("id", "chr", "start", "end", "gene_id", "transcript_id", "exon_number", "exon_id")
      .primaryKeys("id")
      .ifNotExist()
      .create();

schema.vertexLabel("snp")
      .properties("id", "chr", "start", "end", "ref", "alt", "caf_ref", "caf_alt")
      .primaryKeys("id")
      .nullableKeys("ref", "alt", "caf_ref", "caf_alt")
      .ifNotExist()
      .create();

schema.vertexLabel("structural_variant")
      .properties("id", "chr", "start", "end", "variant_accession", "variant_type", "evidence")
      .primaryKeys("id")
      .nullableKeys("evidence")
      .ifNotExist()
      .create();

schema.vertexLabel("sequence_variant")
      .properties("id", "chr", "start", "end", "rsid", "ref", "alt", "raw_cadd_score", "phred_score")
      .primaryKeys("id")
      .nullableKeys("raw_cadd_score", "phred_score")
      .ifNotExist()
      .create();

schema.vertexLabel("enhancer")
      .properties("id", "chr", "start", "end", "data_source", "enhancer_id")
      .primaryKeys("id")
      .nullableKeys("data_source")
      .ifNotExist()
      .create();

schema.vertexLabel("promoter")
      .properties("id", "chr", "start", "end")
      .primaryKeys("id")
      .ifNotExist()
      .create();

schema.vertexLabel("super_enhancer")
      .properties("id", "chr", "start", "end", "se_id")
      .primaryKeys("id")
      .ifNotExist()
      .create();

schema.vertexLabel("non_coding_rna")
      .properties("id", "chr", "start", "end", "rna_type")
      .primaryKeys("id")
      .ifNotExist()
      .create();

schema.vertexLabel("pathway")
      .properties("id", "pathway_name", "evidence")
      .primaryKeys("id")
      .nullableKeys("evidence")
      .ifNotExist()
      .create();

schema.vertexLabel("go")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("uberon")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("clo")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("cl")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("efo")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("bto")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("hpo")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("motif")
      .properties("id", "chr", "start", "end", "tf_name", "pwm_A", "pwm_C", "pwm_G", "pwm_T", "length")
      .primaryKeys("id")
      .ifNotExist()
      .create();

schema.vertexLabel("biological_process")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("molecular_function")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("cellular_component")
      .properties("id", "term_name", "description", "synonyms")
      .primaryKeys("id")
      .nullableKeys("description", "synonyms")
      .ifNotExist()
      .create();

schema.vertexLabel("tad")
      .properties("id", "chr", "start", "end", "genes")
      .primaryKeys("id")
      .ifNotExist()
      .create();

schema.vertexLabel("tfbs")
      .properties("id", "chr", "start", "end")
      .primaryKeys("id")
      .ifNotExist()
      .create();

// Define necessary indexes
schema.indexLabel("geneById")
      .onV("gene")
      .by("id")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("proteinById")
      .onV("protein")
      .by("id")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("geneByName")
      .onV("gene")
      .by("gene_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("proteinByName")
      .onV("protein")
      .by("protein_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("transcriptByName")
      .onV("transcript")
      .by("transcript_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("goByTermName")
      .onV("go")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("biological_processByTermName")
      .onV("biological_process")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("molecular_functionByTermName")
      .onV("molecular_function")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("cellular_componentByTermName")
      .onV("cellular_component")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("uberonByTermName")
      .onV("uberon")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("clByTermName")
      .onV("cl")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("cloByTermName")
      .onV("clo")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("efoByTermName")
      .onV("efo")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("btoByTermName")
      .onV("bto")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("hpoByTermName")
      .onV("hpo")
      .by("term_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("pathwayByName")
      .onV("pathway")
      .by("pathway_name")
      .secondary()
      .ifNotExist()
      .create();

schema.indexLabel("variantByRsid")
      .onV("sequence_variant")
      .by("rsid")
      .secondary()
      .ifNotExist()
      .create();


// Define edge labels
schema.edgeLabel("coexpressed_with")
      .sourceLabel("gene")
      .targetLabel("gene")
      .properties("score")
      .ifNotExist()
      .create();

schema.edgeLabel("interacts_with")
      .sourceLabel("protein")
      .targetLabel("protein")
      .properties("score")
      .ifNotExist()
      .create();

schema.edgeLabel("expressed_in")
      .sourceLabel("gene")
      .targetLabel("ontology_term")
      .properties("score", "p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("expressed_in_uberon")
      .sourceLabel("gene")
      .targetLabel("uberon")
      .properties("score", "p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("expressed_in_clo")
      .sourceLabel("gene")
      .targetLabel("clo")
      .properties("score", "p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("expressed_in_cl")
      .sourceLabel("gene")
      .targetLabel("cl")
      .properties("score", "p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_ontology")
      .sourceLabel("ontology_term")
      .targetLabel("ontology_term")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_cl")
      .sourceLabel("cl")
      .targetLabel("cl")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_clo")
      .sourceLabel("clo")
      .targetLabel("clo")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_uberon")
      .sourceLabel("uberon")
      .targetLabel("uberon")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_efo")
      .sourceLabel("efo")
      .targetLabel("efo")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_bto")
      .sourceLabel("bto")
      .targetLabel("bto")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_hpo")
      .sourceLabel("hpo")
      .targetLabel("hpo")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_bio_process")
      .sourceLabel("biological_process")
      .targetLabel("biological_process")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_mol_function")
      .sourceLabel("molecular_function")
      .targetLabel("molecular_function")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_cell_component")
      .sourceLabel("cellular_component")
      .targetLabel("cellular_component")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("subclass_of_go")
      .sourceLabel("go")
      .targetLabel("go")
      .properties("rel_type")
      .ifNotExist()
      .create();

schema.edgeLabel("belongs_to")
      .sourceLabel("gene")
      .targetLabel("go")
      .properties("qualifier", "db_reference", "evidence")
      .ifNotExist()
      .create();

schema.edgeLabel("involved_in")
      .sourceLabel("protein")
      .targetLabel("biological_process")
      .properties("qualifier", "db_reference", "evidence")
      .ifNotExist()
      .create();

schema.edgeLabel("enables")
      .sourceLabel("protein")
      .targetLabel("molecular_function")
      .properties("qualifier", "db_reference", "evidence")
      .ifNotExist()
      .create();

schema.edgeLabel("part_of")
      .sourceLabel("protein")
      .targetLabel("cellular_component")
      .properties("qualifier", "db_reference", "evidence")
      .ifNotExist()
      .create();

schema.edgeLabel("associated_with_enhancer")
      .sourceLabel("enhancer")
      .targetLabel("gene")
      .properties("score", "biological_context")
      .ifNotExist()
      .create();

schema.edgeLabel("associated_with_super_enhancer")
      .sourceLabel("super_enhancer")
      .targetLabel("gene")
      .properties("biological_context")
      .ifNotExist()
      .create();

schema.edgeLabel("regulates")
      .sourceLabel("gene")
      .targetLabel("gene")
      .properties("evidence", "detection_method", "databases", "evidence_type")
      .ifNotExist()
      .create();

schema.edgeLabel("eqtl_association")
      .sourceLabel("snp")
      .targetLabel("gene")
      .properties("slope", "maf", "p_value", "q_value", "biological_context")
      .ifNotExist()
      .create();

schema.edgeLabel("closest_gene")
      .sourceLabel("snp")
      .targetLabel("gene")
      .properties("chr", "pos", "distance")
      .ifNotExist()
      .create();

schema.edgeLabel("upstream_of")
      .sourceLabel("snp")
      .targetLabel("gene")
      .properties("distance", "p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("downstream_of")
      .sourceLabel("snp")
      .targetLabel("gene")
      .properties("distance", "p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("located_in")
      .sourceLabel("snp")
      .targetLabel("gene")
      .properties("p_value")
      .ifNotExist()
      .create();

schema.edgeLabel("in_ld_with")
      .sourceLabel("snp")
      .targetLabel("snp")
      .properties("ancestry", "r2", "d_prime")
      .ifNotExist()
      .create();

schema.edgeLabel("tfbs_snp")
      .sourceLabel("gene")
      .targetLabel("snp")
      .properties("effect", "score")
      .ifNotExist()
      .create();

schema.edgeLabel("binds_to")
      .sourceLabel("gene")
      .targetLabel("tfbs")
      .properties("score")
      .ifNotExist()
      .create();

schema.edgeLabel("activity_by_contact")
      .sourceLabel("snp")
      .targetLabel("gene")
      .properties("score", "biological_context")
      .ifNotExist()
      .create();

schema.edgeLabel("chromatin_state_uberon")
      .sourceLabel("snp")
      .targetLabel("uberon")
      .properties("state")
      .ifNotExist()
      .create();

schema.edgeLabel("chromatin_state_cl")
      .sourceLabel("snp")
      .targetLabel("cl")
      .properties("state")
      .ifNotExist()
      .create();

schema.edgeLabel("chromatin_state_clo")
      .sourceLabel("snp")
      .targetLabel("clo")
      .properties("state")
      .ifNotExist()
      .create();

schema.edgeLabel("histone_modification_uberon")
      .sourceLabel("snp")
      .targetLabel("uberon")
      .properties("modification")
      .ifNotExist()
      .create();

schema.edgeLabel("histone_modification_cl")
      .sourceLabel("snp")
      .targetLabel("cl")
      .properties("modification")
      .ifNotExist()
      .create();

schema.edgeLabel("histone_modification_clo")
      .sourceLabel("snp")
      .targetLabel("clo")
      .properties("modification")
      .ifNotExist()
      .create();