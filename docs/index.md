# BioCypher-KG Documentation

Welcome to the BioCypher-KG documentation. This index maps every document to its audience and purpose.

---

## Start here

| Audience | First doc to read |
|---|---|
| New contributor | [project-structure](development/project-structure.md) → [local-development](development/local-development.md) → [coding-standards](development/coding-standards.md) |
| Developer integrating the API | [system-overview](architecture/system-overview.md) → [endpoints](api/endpoints.md) → [schemas](api/schemas.md) |
| Operator deploying the system | [deployment](operations/deployment.md) → [configuration](operations/configuration.md) → [monitoring](operations/monitoring.md) |
| Researcher querying the KG | [data-model](knowledge-graph/data-model.md) → [adapter-catalog](knowledge-graph/adapter-catalog.md) → [faq](reference/faq.md) |

---

## Architecture

| Document | Purpose |
|---|---|
| [system-overview](architecture/system-overview.md) | End-to-end system diagram, species/format matrices, key source files |
| [architecture](architecture/architecture.md) | Component dependency graph, architectural principles, known gaps |
| [data-flow](architecture/data-flow.md) | Pipeline sequence diagram, checkpoint state machine, versioning flow |
| [component-diagrams](architecture/component-diagrams.md) | Mermaid class hierarchy for adapters, writers, processors, services |

## Development

| Document | Purpose |
|---|---|
| [local-development](development/local-development.md) | Setup, sample run, environment variables |
| [project-structure](development/project-structure.md) | Every directory and file with purpose annotations |
| [coding-standards](development/coding-standards.md) | Adapter contract, schema patterns, PR checklist |
| [testing](development/testing.md) | Test modes, CI integration, adding tests |

## Operations

| Document | Purpose |
|---|---|
| [deployment](operations/deployment.md) | Docker deployment of Neo4j, MORK, and kg-service |
| [configuration](operations/configuration.md) | All config files, env vars, CLI flags — complete reference |
| [monitoring](operations/monitoring.md) | Dataset staleness, SonarQube, cache refresh, health checks |
| [troubleshooting](operations/troubleshooting.md) | Common failures and resolutions |

## API

| Document | Purpose |
|---|---|
| [endpoints](api/endpoints.md) | All REST endpoints with parameters and response shapes |
| [schemas](api/schemas.md) | Pydantic models, `graph_info.json`, `VersionInfo` dataclass |

## Knowledge Graph

| Document | Purpose |
|---|---|
| [data-model](knowledge-graph/data-model.md) | All 36+ node types and 108+ edge types — complete reference |
| [adapter-catalog](knowledge-graph/adapter-catalog.md) | All 40+ data sources: biology, species, node/edge types, URLs |
| [ontology](knowledge-graph/ontology.md) | 16 integrated ontologies, CURIE prefixes, fetch behavior |
| [ingestion-pipeline](knowledge-graph/ingestion-pipeline.md) | Download → adapt → write flow, provenance chain |
| [graph-construction](knowledge-graph/graph-construction.md) | BioCypher integration, schema merging, ID conventions |
| [writers](knowledge-graph/writers.md) | All 7 output formats — Neo4j CSV, MeTTa, Prolog, Parquet, KGX, NetworkX |

## Reference

| Document | Purpose |
|---|---|
| [glossary](reference/glossary.md) | Technical and biological term definitions |
| [faq](reference/faq.md) | Common questions across all audiences |

---

## Existing documentation (do not duplicate)

These files exist in the repository and should be linked to, not restated:

| File | Content |
|---|---|
| [README](https://github.com/rejuve-bio/biocypher-kg/blob/main/README.md) | Quickstart, make commands, Neo4j deployment |
| [CONTRIBUTING](https://github.com/rejuve-bio/biocypher-kg/blob/main/CONTRIBUTING.md) | Adapter development guide, PR workflow |
| [dataset-versioning](knowledge-graph/dataset-versioning.md) | Complete versioning specification (moved from doc/) |
| [biocypher_metta/processors/README](https://github.com/rejuve-bio/biocypher-kg/blob/main/biocypher_metta/processors/README.md) | Processor usage and cache files |
| [schema_generator/README](https://github.com/rejuve-bio/biocypher-kg/blob/main/schema_generator/README.md) | Schema generation tool |
| [biocypher_dataset_downloader/versioning/README](https://github.com/rejuve-bio/biocypher-kg/blob/main/biocypher_dataset_downloader/versioning/README.md) | VersionInfo/VersionGetter contract |
