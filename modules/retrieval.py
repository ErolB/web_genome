# functions for retrieving genomic data

import subprocess
import os
import ftplib
import csv
import json

from modules.utils import *
from modules.file_tools import *

# search PATRIC by organism name
def search_by_name(organism_name):
    try:
        output = subprocess.check_output('p3-all-genomes --eq organism_name,%s --attr organism_name' % organism_name, shell=True)
    except subprocess.CalledProcessError:
        return None
    results = csv.DictReader(output.decode().split('\n'), delimiter='\t')
    results = list(results)
    genomes = []
    for item in results:
        item = item.replace(' ', '')
        if item:
            new_genome = Genome(item['genome.organism_name'], id=item['genome.genome_id'])
            genomes.append(new_genome)
    return genomes

# search PATRIC by taxon ID
def search_by_id(organism_name):
    output = subprocess.check_output('p3-all-genomes --eq genome_id,%s --attr organism_name' % organism_name, shell=True)
    results = csv.DictReader(output.decode().split('\n'), delimiter='\t')
    results = list(results)
    genomes = []
    for item in results:
        new_genome = Genome(item['genome.organism_name'], id=item['genome.genome_id'])
        genomes.append(new_genome)
    return genomes

# retrieve gene sequences from PATRIC (if genome was obtained there)
def retrieve_sequences(genome_info):
    genomes = []
    ftp = ftplib.FTP('ftp.patricbrc.org')
    ftp.login()
    for entry in genome_info:
        entry = json.loads(entry)
        entry_id = entry['id']
        entry_name = entry['name']
        raw_text = []
        ftp.retrbinary('RETR genomes/%s/%s.PATRIC.faa' % (entry_id, entry_id), raw_text.append, 1024)
        file_text = ''
        for item in raw_text:
            file_text += item.decode('utf-8')
        genome = Genome(organism=entry_name, id=entry_id)
        gene_dict = parse_patric_fasta(file_text)
        for gene in gene_dict.keys():
            genome.add_gene_obj(gene, gene_dict[gene])
        genomes.append(genome)
    return genomes

# reads a FASTA file and creates a list of Genome objects
def read_genomes(file_path):
    genomes = {}
    gene_file = open(file_path, 'r')
    data = gene_file.read()
    genes = data.split('>')
    for gene in genes:
        if not gene:
            continue
        header, sequence = gene.split('\n', 1)
        sequence = sequence.replace('\n', '')  # removes spaces
        title, description = header.split('|')
        organism, locus = title.split('@')
        if organism in list(genomes.keys()):
            genomes[organism].add_gene(locus, sequence, description=description)
        else:
            genomes[organism] = Genome(organism)
            genomes[organism].add_gene(locus, sequence, description=description)
    return list(genomes.values())

# reads the contents of a directory and returns a dictionary mapping file names to full paths
def read_dir(path):
    file_dict = {}
    files = os.listdir(path)
    for item in files:
        file_dict[item] = path + '/' + item
    return file_dict