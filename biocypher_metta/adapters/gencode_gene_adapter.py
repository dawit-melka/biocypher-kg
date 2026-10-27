import gzip
from pathlib import Path
from biocypher_metta.adapters import Adapter
from biocypher_metta.adapters.helpers import check_genomic_location
from biocypher_metta.harmonization.aliases import ALIAS_PAYLOAD_KEY, AliasCollector
from biocypher_metta.harmonization.fingerprint import version_stamp
from biocypher_metta.processors import HGNCProcessor, EntrezEnsemblProcessor
from biocypher_metta.processors.entrez_ensembl_processor import gene_info_record

# Human data:
# https://www.gencodegenes.org/human/

# Example gencode vcf input file:
# ##description: evidence-based annotation of the human genome (GRCh38), version 42 (Ensembl 108)
# ##provider: GENCODE
# ##contact: gencode-help@ebi.ac.uk
# ##format: gtf
# ##date: 2022-07-20
# chr1    HAVANA  gene    11869   14409   .       +       .       gene_id "ENSG00000290825.1"; gene_type "lncRNA"; gene_name "DDX11L2"; level 2; tag "overlaps_pseudogene";
# chr1    HAVANA  transcript      11869   14409   .       +       .       gene_id "ENSG00000290825.1"; transcript_id "ENST00000456328.2"; gene_type "lncRNA"; gene_name "DDX11L2"; transcript_type "lncRNA"; transcript_name "DDX11L2-202"; level 2; transcript_support_level "1"; tag "basic"; tag "Ensembl_canonical"; havana_transcript "OTTHUMT00000362751.1";
# chr1    HAVANA  exon    11869   12227   .       +       .       gene_id "ENSG00000290825.1"; transcript_id "ENST00000456328.2"; gene_type "lncRNA"; gene_name "DDX11L2"; transcript_type "lncRNA"; transcript_name "DDX11L2-202"; exon_number 1; exon_id "ENSE00002234944.1"; level 2; transcript_support_level "1"; tag "basic"; tag "Ensembl_canonical"; havana_transcript "OTTHUMT00000362751.1";
# chr1    HAVANA  exon    12613   12721   .       +       .       gene_id "ENSG00000290825.1"; transcript_id "ENST00000456328.2"; gene_type "lncRNA"; gene_name "DDX11L2"; transcript_type "lncRNA"; transcript_name "DDX11L2-202"; exon_number 2; exon_id "ENSE00003582793.1"; level 2; transcript_support_level "1"; tag "basic"; tag "Ensembl_canonical"; havana_transcript "OTTHUMT00000362751.1";

# Mouse data:
# https://www.gencodegenes.org/mouse/


# Fly data:
# https://ftp.ebi.ac.uk/ensemblgenomes/pub/metazoa/current/gtf/drosophila_melanogaster/

# Example gencode vcf input file:
# Dmel:
# 3R	FlyBase	gene	17750129	17763188	.	-	.	gene_id "FBgn0038542"; gene_name "TyrR"; gene_source "FlyBase"; gene_biotype "protein_coding";
# 3R	FlyBase	transcript	17750129	17758978	.	-	.	gene_id "FBgn0038542"; transcript_id "FBtr0344474"; gene_name "TyrR"; gene_source "FlyBase"; gene_biotype "protein_coding"; transcript_name "TyrR-RB"; transcript_source "FlyBase"; transcript_biotype "protein_coding";
# 3R	FlyBase	exon	17758709	17758978	.	-	.	gene_id "FBgn0038542"; transcript_id "FBtr0344474"; exon_number "1"; gene_name "TyrR"; gene_source "FlyBase"; gene_biotype "protein_coding"; transcript_name "TyrR-RB"; transcript_source "FlyBase"; transcript_biotype "protein_coding"; exon_id "FBtr0344474-E1";
# 3R	FlyBase	exon	17757024	17757709	.	-	.	gene_id "FBgn0038542"; transcript_id "FBtr0344474"; exon_number "2"; gene_name "TyrR"; gene_source "FlyBase"; gene_biotype "protein_coding"; transcript_name "TyrR-RB"; transcript_source "FlyBase"; transcript_biotype "protein_coding"; exon_id "FBtr0344474-E2";

# dmelSummaries: table
#FBgn_ID	Gene_Symbol	Summary_Source	Summary


class GencodeGeneAdapter(Adapter):
    ALLOWED_KEYS = ['gene_id', 'gene_type', 'gene_biotype', 'gene_name',
                    'transcript_id', 'transcript_type', 'transcript_name', 'hgnc_id', 'mgi_id',
                    'havana_gene']
    INDEX = {'chr': 0, 'type': 2, 'coord_start': 3, 'coord_end': 4, 'info': 8}

    SUPPORTS_ALIASES = True
    ALIAS_LEGACY_PROPS = ('synonym',)
    HGNC_CACHE_DIR = 'aux_files/hsa/hgnc'

    def __init__(self, write_properties, add_provenance, taxon_id, filepath, label,
                 gene_alias_file_path=None, chr=None, start=None, end=None):

        self.filepath = filepath
        self.chr = chr
        self.start = start
        self.end = end
        self.label = label
        self.taxon_id = taxon_id
        self.dataset = 'gencode_gene'
        self.gene_alias_file_path = gene_alias_file_path
        self.source = 'GENCODE'
        self.version = 'v49'                                # file name:  gencode.v49.annotation.gtf.gz
        version = str(filepath).split('/')[-1]
        version = version.split('.')[1]
        if version.startswith('v'):
            self.version = version
        self.source_url = 'https://www.gencodegenes.org/'

        self.hgnc_processor = HGNCProcessor()
        self.hgnc_processor.load_or_update()

        # Pre-load gene aliases: use processor if no NCBI gene_info file is provided
        self.entrez_processor = None
        self._gene_info_records = None
        if gene_alias_file_path:
            self.gene_aliases = self.get_gene_alias()
        else:
            species_info = Adapter.SPECIES_INFO[taxon_id]
            processor = EntrezEnsemblProcessor(
                ncbi_gene_info_url=species_info['ncbi_gene_info_url'],
                gencode_url=species_info['features_data_url'],
                tax_id=str(taxon_id),
                cache_dir=species_info['entrez_ensembl_cache_directory'],
                update_interval_hours=species_info['update_interval_hours']
            )
            processor.load_or_update()
            self.gene_aliases = processor.gene_aliases
            self.entrez_processor = processor

        super(GencodeGeneAdapter, self).__init__(write_properties, add_provenance)

    @classmethod
    def alias_fingerprint_deps(cls, args):
        deps = {}
        taxon_id = args.get('taxon_id')
        if taxon_id == 9606:
            deps['hgnc'] = version_stamp(Path(cls.HGNC_CACHE_DIR) / 'hgnc_version.json')
        cache_dir = Adapter.SPECIES_INFO.get(taxon_id, {}).get('entrez_ensembl_cache_directory')
        if cache_dir and not args.get('gene_alias_file_path'):
            deps['entrez_ensembl'] = version_stamp(Path(cache_dir) / 'entrez_ensembl_version.json')
        return deps

    def gene_info_records(self):
        """Typed NCBI gene_info records keyed by gene ID and 'HGNC:<n>' (alias mode only)."""
        if self._gene_info_records is None:
            if self.gene_alias_file_path:
                records = {}
                with gzip.open(self.gene_alias_file_path, 'rt') as input:
                    next(input)
                    for line in input:
                        fields = line.rstrip('\n').split('\t')
                        if len(fields) < 16 or fields[0] != str(self.taxon_id):
                            continue
                        record = gene_info_record(fields)
                        if record:
                            for key in record['gene_ids'] + ([record['hgnc_id']] if record['hgnc_id'] else []):
                                records[key] = record
                self._gene_info_records = records
            else:
                self._gene_info_records = self.entrez_processor.gene_info_records
        return self._gene_info_records

    def gene_alias_payload(self, raw_id, info, result):
        """Typed aliases for one gene from data the adapter already holds."""
        aliases = AliasCollector(source=self.source)
        current = result['current'] if result['status'] not in ('unknown', 'ensembl_only') else None
        human = self.taxon_id == 9606
        aliases.add(current, 'approved_symbol', source='HGNC' if human else self.source)
        if result['status'] == 'updated':
            aliases.add(result['original'], 'previous_symbol')

        hgnc_id = info.get('hgnc_id')
        aliases.add(hgnc_id, 'xref', 'HGNC')
        aliases.add(info.get('havana_gene'), 'xref', 'HAVANA')
        aliases.add(info.get('mgi_id'), 'xref', 'MGI')

        if human and current:
            record = self.hgnc_processor.get_symbol_record(current)
            aliases.extend(record['previous_symbols'], 'previous_symbol', source='HGNC')
            aliases.extend(record['alias_symbols'], 'alias_symbol', source='HGNC')
            aliases.add(record['name'], 'full_name', source='HGNC')
            aliases.add(record['entrez_id'], 'xref', 'NCBIGene', source='HGNC')
            aliases.add(record['hgnc_id'], 'xref', 'HGNC', source='HGNC')

        records = self.gene_info_records()
        ncbi = records.get(raw_id) or (records.get(hgnc_id) if hgnc_id else None)
        if ncbi:
            aliases.add(ncbi['entrez_id'], 'xref', 'NCBIGene', source='NCBI Gene')
            aliases.add(ncbi['nomenclature_symbol'], 'approved_symbol', source='NCBI Gene')
            if ncbi['symbol'] != ncbi['nomenclature_symbol']:
                aliases.add(ncbi['symbol'], 'alias_symbol', source='NCBI Gene')
            aliases.extend(ncbi['synonyms'], 'alias_symbol', source='NCBI Gene')
            aliases.add(ncbi['full_name'], 'full_name', source='NCBI Gene')
            aliases.extend(ncbi['other_designations'], 'other_designation', source='NCBI Gene')
            aliases.add(ncbi['hgnc_id'], 'xref', 'HGNC', source='NCBI Gene')
        return aliases.to_list()
 

    def parse_info_metadata(self, info):
        parsed_info = {}
        for key, value in zip(info, info[1:]):
            if key in GencodeGeneAdapter.ALLOWED_KEYS:
                parsed_info[key] = value.replace('"', '').replace(';', '')
        return parsed_info

    # the gene alias dict will use both ensembl id and hgnc id as key
    def get_gene_alias(self):
        alias_dict = {}
        with gzip.open(self.gene_alias_file_path, 'rt') as input:
            next(input)
            for line in input:
                (tax_id, gene_id, symbol, locus_tag, synonyms, dbxrefs, chromosome, map_location, description, type_of_gene, symbol_from_nomenclature_authority,
                 full_name_from_nomenclature_authority, Nomenclature_status, Other_designations, Modification_date, Feature_type) = line.split('\t')

                split_dbxrefs = dbxrefs.split('|')
                hgnc = ''
                ensembl = ''
                flybase = ''                    # NEEED TO CHANGE THIS!
                for ref in split_dbxrefs:
                    if ref.startswith('HGNC:'):
                        hgnc = ref[5:]
                    if ref.startswith('Ensembl:'):
                        ensembl = ref[8:]
                    if ref.upper().startswith('FLYBASE:'):
                        flybase = ref[8:]
                if ensembl or hgnc or flybase:
                    complete_synonyms = []
                    complete_synonyms.append(symbol)
                    for i in synonyms.split('|'):
                        complete_synonyms.append(i)
                    if hgnc:
                        complete_synonyms.append(hgnc)
                    for i in Other_designations.split('|'):
                        complete_synonyms.append(i)
                    complete_synonyms.append(
                        symbol_from_nomenclature_authority)
                    complete_synonyms.append(
                        full_name_from_nomenclature_authority)
                    complete_synonyms = list(set(complete_synonyms))
                    if '-' in complete_synonyms:
                        complete_synonyms.remove('-')
                    if ensembl:
                        alias_dict[ensembl] = complete_synonyms
                    if hgnc:
                        alias_dict[hgnc] = complete_synonyms
                    if flybase:
                        complete_synonyms.append(flybase)
                        alias_dict[flybase] = complete_synonyms
        return alias_dict

    def get_nodes(self):
        alias_dict = self.gene_aliases
        not_processed = 0
        processed_records = 0
        with gzip.open(self.filepath, 'rt') as input:
            for line in input:
                if line.startswith('#'):
                    continue
                split_line = line.strip().split()
                if split_line[GencodeGeneAdapter.INDEX['type']] == 'gene':
                    info = self.parse_info_metadata(
                        split_line[GencodeGeneAdapter.INDEX['info']:])
                    gene_id = info['gene_id']
                    raw_id = gene_id.split('.')[0]
                    
                    # Determine CURIE prefix
                    id_prefix = GencodeGeneAdapter.CURIE_PREFIX[self.taxon_id]
                    id = f"{id_prefix}:{raw_id}"
                    if gene_id.endswith('_PAR_Y'):
                        id = f"{id_prefix}:{raw_id}_PAR_Y"

                    alias = alias_dict.get(raw_id)
                    if not alias:
                        hgnc_id = info.get('hgnc_id')
                        if hgnc_id:
                            # Alias dicts key HGNC entries as 'HGNC:<n>' (NCBI dbXrefs
                            # read 'HGNC:HGNC:<n>' and drop the first prefix).
                            alias = alias_dict.get(hgnc_id) or alias_dict.get(hgnc_id.replace('HGNC:', ''))
                    
                    chr = split_line[GencodeGeneAdapter.INDEX['chr']]
                    start = int(split_line[GencodeGeneAdapter.INDEX['coord_start']])
                    end = int(split_line[GencodeGeneAdapter.INDEX['coord_end']])
                    
                    gene_name = info.get('gene_name')
                    if not gene_name:
                        # print(f"No gene name found for gene {gene_id}. Invalid record: {info}. Skipping it.")
                        not_processed += 1
                        continue

                    if self.taxon_id == 9606:       # human
                        result = self.hgnc_processor.process_identifier(gene_name)
                    else:
                        result = {
                            'status': 'current',
                            'original': gene_name,
                            'current': gene_name
                        }

                    props = {}
                    try:
                        if check_genomic_location(self.chr, self.start, self.end, chr, start, end):
                            if self.write_properties:
                                gene_type_val = info.get('gene_type')
                                props = {
                                    'gene_type': gene_type_val if gene_type_val is not None else info['gene_biotype'],
                                    'chr': chr if chr else 'unknown',
                                    'start': start if start else 'unknown',
                                    'end': end if end else 'unknown',
                                    'gene_name': 'unknown' if result['status'] == 'unknown' or result['status'] == 'ensembl_only' else result['current'],
                                    'synonym': alias,
                                    'taxon_id': self.taxon_id,
                                }
                                if result['status'] == 'updated':
                                    props['old_gene_name'] = result['original']
                                if self.add_provenance:
                                    props['source'] = self.source
                                    props['source_url'] = self.source_url
                            if self.emit_aliases:
                                props[ALIAS_PAYLOAD_KEY] = self.gene_alias_payload(raw_id, info, result)
                            processed_records += 1
                            yield id, self.label, props
                        else:
                            not_processed += 1
                    except Exception as e:
                        print(f'Failed to process line: {line}\nError: {str(e)}')
                        not_processed += 1
        