# functions for retrieving genomic data

import subprocess
import os
import ftplib
import csv
import json
import requests
import threading
import queue

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
'''
def search_by_id(organism_name):
    output = subprocess.check_output('p3-all-genomes --eq genome_id,%s --attr organism_name' % organism_name, shell=True)
    results = csv.DictReader(output.decode().split('\n'), delimiter='\t')
    results = list(results)
    genomes = []
    for item in results:
        new_genome = Genome(item['genome.organism_name'], id=item['genome.genome_id'])
        genomes.append(new_genome)
    return genomes
'''

# uses API to search by taxon ID
def search_by_ids(id_list):
    genomes = []
    request_url = "https://www.patricbrc.org/api/genome/?in(genome_id,(%s))&select(genome_name, genome_id)&limit(100000,0)" \
                  "&http_accept=application/json" % ','.join(id_list)
    try:
        raw_data = requests.get(request_url).content
    except:
        return 'error'
    for item in json.loads(raw_data):
        new_genome = Genome(item['genome_name'], item['genome_id'])
        genomes.append(new_genome)
    return genomes


# retrieve gene sequences from PATRIC (if genome was obtained there)
def retrieve_sequences(genome_info, worker_count=5):
    genomes = queue.Queue(maxsize=100)
    def get_genomes(entry_list, data_queue):
        for entry in entry_list:
            ftp = ftplib.FTP('ftp.patricbrc.org')
            ftp.login()
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
            data_queue.put(genome)
    # use multiple threads to get genomes
    max_load = int(len(genome_info)/worker_count) + 1
    threads = []
    done = False
    for i in range(worker_count):
        if done:
            break
        thread_tasks = []
        for j in range(max_load):
            current_index = (max_load*i) + j
            if current_index >= len(genome_info):
                done = not done
                break
            thread_tasks.append(genome_info[current_index])
        current_thread = threading.Thread(target=get_genomes, args=(thread_tasks, genomes))
        current_thread.start()
        threads.append(current_thread)
    # wait for threads to finish
    for thread in threads:
        thread.join()
    # retrieve data
    genome_list = []
    while not genomes.empty():
        genome_list.append(genomes.get())
    return genome_list

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