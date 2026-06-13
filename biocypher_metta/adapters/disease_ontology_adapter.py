
import os
from biocypher._logger import logger
from biocypher_metta.adapters.ontologies_adapter import OntologyAdapter

class DiseaseOntologyAdapter(OntologyAdapter):
    @classmethod
    def _get_ontologies(cls):
        api_key = os.getenv('BIOPORTAL_API_KEY')
        if not api_key:
            # No key (e.g. CI without the secret, or a full sample run): disable the
            # adapter instead of hard-failing the whole pipeline. It yields nothing in
            # this state; set BIOPORTAL_API_KEY in your .env to ingest the Disease Ontology.
            logger.warning(
                "BIOPORTAL_API_KEY not set; DiseaseOntologyAdapter is disabled and will "
                "yield no nodes/edges. Set it in your .env to ingest the Disease Ontology."
            )
            return {}
        return {
            # 'do': 'https://purl.obolibrary.org/obo/do.owl'
            # Sometimes the above link doesn't respond. This is an alternative:
            'do': f'https://data.bioontology.org/ontologies/DOID/submissions/654/download?apikey={api_key}'
        }

    def __init__(self, write_properties, add_provenance, ontology, type, label='disease', dry_run=False, add_description=False, cache_dir=None):
        self.ONTOLOGIES = self._get_ontologies()
        self._enabled = bool(self.ONTOLOGIES)
        super(DiseaseOntologyAdapter, self).__init__(write_properties, add_provenance, ontology, type, label, dry_run, add_description, cache_dir)

    def get_nodes(self):
        if not self._enabled:
            return
        yield from super().get_nodes()

    def get_edges(self):
        if not self._enabled:
            return
        yield from super().get_edges()


    def get_ontology_source(self):
        """
        Returns the source and source URL for Disease Ontology (DO).
        """
        return 'Disease Ontology', 'https://purl.obolibrary.org/obo/do.owl' 

    def get_uri_prefixes(self):
        """Define URI prefixes for Sequence Ontology."""
        return {
            'primary': 'http://purl.obolibrary.org/obo/DOID_',
            'clo': 'http://purl.obolibrary.org/obo/CL_',
        }                