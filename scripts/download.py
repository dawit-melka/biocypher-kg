# Author Abdulrahman S. Omar <xabush@singularitynet.io>
import typer
import pathlib
import os
import requests
from tqdm import tqdm
import shutil
import yaml
import contextlib
from google.cloud import storage
from typing_extensions import Annotated

app = typer.Typer()

def download(url, filepath):
    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code != 200:
        r.raise_for_status()
        raise RuntimeError(f"Request to {url} returned status code {r.status_code}")

    file_size = int(r.headers.get("Content-Length", 0))

    desc = "(Unknown total file size)" if file_size == 0 else ""

    with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
        with filepath.open("wb") as f:
            shutil.copyfileobj(r_raw, f)

def download_gencode(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/gencode")
    save_dir.mkdir(parents=True, exist_ok=True)
    p = save_dir.joinpath("gencode.annotation.gtf.gz")
    download(url, p)

def download_uniprot(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/uniprot")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_reactome(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    urls = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/reactome")
    save_dir.mkdir(parents=True, exist_ok=True)
    for url in urls:
        filename = url.split("/")[-1]
        p = save_dir.joinpath(filename)
        r = requests.get(url, stream=True, allow_redirects=True,)
        if r.status_code != 200:
            r.raise_for_status()
            raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
        with p.open("w") as f:
            f.write(r.text)

def download_gaf(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/go")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_coxpressdb(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    filename = "coxpress_db.zip"
    save_dir = pathlib.Path(f"{output_dir}/coxpressdb")
    save_dir.mkdir(parents=True, exist_ok=True)
    p = save_dir.joinpath(filename)
    download(url, p)
    print(f"Extracting files in coxpressdb ....")
    shutil.unpack_archive(p, save_dir)

def download_tflink(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    filename = "tflink_homo_sapiens_interactions.tsv.gz"
    save_dir = pathlib.Path(f"{output_dir}/tflink")
    save_dir.mkdir(parents=True, exist_ok=True)
    p = save_dir.joinpath(filename)
    download(url, p)

def download_string(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    filename = "string_human_ppi_v12.0.txt.gz"
    save_dir = pathlib.Path(f"{output_dir}/string")
    save_dir.mkdir(parents=True, exist_ok=True)
    p = save_dir.joinpath(filename)
    download(url, p)

def download_tadmap(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/tadmap")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p, verify=False) #tadmap site doesn't use https


def download_roadmap(output_dir, config):
    """
    Download Roadmap Epigenomics chromatin state data
    There are 128 cell lines, each with 25 states.
    """

    print(f"Downloading from {config['name']} .....")
    root_url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/roadmap")
    save_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 130):

        if i == 60 or i == 64: # E060 & E064 are missing
            continue
        if i < 100:
            file_name = f"E0{i:02d}_25_imputed12marks_mnemonics.bed.gz"
        else:
            file_name = f"E{i}_25_imputed12marks_mnemonics.bed.gz"
        url = f"{root_url}/{file_name}"
        p = save_dir.joinpath(file_name)
        download(url, p)

def download_gtex_eQTL(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    bucket_name = config["bucket"]
    obj_path = config["path"]
    filename = obj_path.split("/")[-1]
    save_dir = pathlib.Path(f"{output_dir}/gtex/eqtl")
    save_dir.mkdir(parents=True, exist_ok=True)
    p = save_dir.joinpath(filename)

    # storage_client = storage.Client("gtex")
    # bucket = storage_client.bucket(bucket_name)
    # blob = bucket.blob(obj_path)
    # blob.download_to_filename(p)

    shutil.unpack_archive(p, save_dir)


def download_topld(output_dir, config, chr=None):
    print(f"Downloading from {config['name']} .....")
    if chr is not None:
        for pop, url in config["url"].items():
            print(f"Downloading {chr} for {pop} .....")
            url = url.replace("xx", chr)
            save_dir = pathlib.Path(f"{output_dir}/topld/{pop}")
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = url.split("/")[-1]
            p = save_dir.joinpath(filename)
            download(url, p)
    else: # download all chromosomes
        chrs = [f"chr{chr}" for chr in range(1, 23)]
        chrs.append("chrX")
        for pop, url in config["url"].items():
            for chr in chrs:
                print(f"Downloading {chr} for {pop} .....")
                url = url.replace("xx", chr)
                save_dir = pathlib.Path(f"{output_dir}/topld/{pop}")
                save_dir.mkdir(parents=True, exist_ok=True)
                filename = url.split("/")[-1]
                p = save_dir.joinpath(filename)
                download(url, p)

def download_hocomoco(output_dir, config):
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    #Download the annotation file
    save_dir = pathlib.Path(f"{output_dir}/hocomoco")
    save_dir.mkdir(parents=True, exist_ok=True)
    annotation_url = url["annotation"]
    filename = annotation_url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(annotation_url, p)
    #Download the pwm files
    pwm_url = url["pwm"]
    filename = pwm_url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(pwm_url, p)
    shutil.unpack_archive(p, save_dir)

def download_favor(output_dir, config, chr=None):
    print(f"Downloading from {config['name']} .....")
    save_dir = pathlib.Path(f"{output_dir}/favor")
    save_dir.mkdir(parents=True, exist_ok=True)
    if chr is not None:
        if chr == "chrX": #currently favor doesn't have annotations for SNVs on chrX
            print(f"No download url for {chr}")
        url = config["url"][chr]
        filename = f"{chr}.tar.gz"
        p = save_dir.joinpath(filename)
        download(url, p)
    else:
        for c, url in config["url"].items():
            filename = f"{c}.tar.gz"
            p = save_dir.joinpath(filename)
            download(url, p)
def download_abc(output_dir, config):
    """Download Activity-By-Contact (ABC) data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/abc")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_refseq_closest_gene(output_dir, config):
    """Download RefSeq Closest Gene data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/refseq")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_roadmap_dhs(output_dir, config):
    """Download RoadMap DHS data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/roadmap/dhs")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_roadmap_state(output_dir, config):
    """Download Roadmap Epigenomics State data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/roadmap/state")
    save_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 130):
        if i == 60 or i == 64:  # E060 & E064 are missing
            continue
        if i < 100:
            file_name = f"E0{i:02d}_25_imputed12marks_statecalls.bed.gz"
        else:
            file_name = f"E{i}_25_imputed12marks_statecalls.bed.gz"
        file_url = f"{url}/{file_name}"
        p = save_dir.joinpath(file_name)
        download(file_url, p)

def download_roadmap_h3marks(output_dir, config):
    """Download Roadmap Epigenomics H3 Marks data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/roadmap/h3marks")
    save_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 130):
        if i == 60 or i == 64:  # E060 & E064 are missing
            continue
        if i < 100:
            file_name = f"E0{i:02d}_12_marks_imputed.bed.gz"
        else:
            file_name = f"E{i}_12_marks_imputed.bed.gz"
        file_url = f"{url}/{file_name}"
        p = save_dir.joinpath(file_name)
        download(file_url, p)

def download_tfbs(output_dir, config):
    """Download TFBS Clusters data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/tfbs")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_bgee(output_dir, config):
    """Download Bgee Expression data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/bgee")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_rna_central(output_dir, config):
    """Download RNA Central data"""
    print(f"Downloading from {config['name']} .....")
    urls = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/rna_central")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    for data_type, url in urls.items():
        filename = url.split("/")[-1]
        p = save_dir.joinpath(filename)
        download(url, p)

def download_enhancer_atlas(output_dir, config):
    """Download EnhancerAtlas data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/enhancer_atlas")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)
def download_dbsuper(output_dir, config):
    """Download DBSuper super enhancer data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/dbsuper")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_dbsnp(output_dir, config):
    """Download dbSNP data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/dbsnp")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)

def download_gwas(output_dir, config):
    """Download GWAS Catalog data"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/gwas")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = "gwas-catalog-associations_ontology-annotated.tsv"
    p = save_dir.joinpath(filename)
    download(url, p)

def download_brenda_tissue_ontology(output_dir, config):
    """Download Brenda Tissue Ontology"""
    print(f"Downloading from {config['name']} .....")
    url = config["url"]
    save_dir = pathlib.Path(f"{output_dir}/brenda_tissue_ontology")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1]
    p = save_dir.joinpath(filename)
    download(url, p)


@app.command()
def download_data(output_dir: Annotated[pathlib.Path, typer.Option(exists=False, file_okay=False, dir_okay=True)],
                 chr: str = None):
    """
    Download all the source data for biocypher-metta import
    """
    with open("config/data_source_config.yaml", "r") as f:
        try:
            config = yaml.safe_load(f)
            pathlib.Path(output_dir).mkdir(exist_ok=True, parents=True)
            
            # Existing downloads
            download_gencode(output_dir, config["gencode"])
            download_uniprot(output_dir, config["uniprot"])
            download_reactome(output_dir, config["reactome"])
            download_gaf(output_dir, config["gaf"])
            download_coxpressdb(output_dir, config["coxpressdb"])
            download_tflink(output_dir, config["tflink"])
            download_string(output_dir, config["string"])
            download_tadmap(output_dir, config["tadmap"])
            download_roadmap(output_dir, config["roadmap"])
            download_gtex_eQTL(output_dir, config["gtex_eqtl"])
            download_topld(output_dir, config["topld"], chr)
            download_hocomoco(output_dir, config["hocomoco"])
            download_favor(output_dir, config["favor"], chr)
            
            # New downloads
            download_abc(output_dir, config["abc"])
            download_refseq_closest_gene(output_dir, config["refseq_closest_gene"])
            download_roadmap_dhs(output_dir, config["roadmap_dhs"])
            download_roadmap_state(output_dir, config["roadmap_state"])
            download_roadmap_h3marks(output_dir, config["roadmap_h3marks"])
            download_tfbs(output_dir, config["tfbs"])
            download_bgee(output_dir, config["bgee"])
            download_rna_central(output_dir, config["rna_central"])
            download_enhancer_atlas(output_dir, config["enhancer_atlas"])
            download_dbsuper(output_dir, config["dbsuper"])
            download_dbsnp(output_dir, config["dbsnp"])
            download_gwas(output_dir, config["gwas"])
            download_brenda_tissue_ontology(output_dir, config["brenda_tissue_ontology"])
            
        except yaml.YAMLError as exc:
            print(f"Error parsing config file: {exc}")

if __name__ == "__main__":
    app()