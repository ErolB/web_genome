'''
Created on : 1/27/2018
Author: Erol Bahadiroglu
Deprecated: functionality moved to retrieval.py
'''

from modules.utils import Genome, Gene
import os
import re
import subprocess
import shutil


# reads the contents of a directory and returns a dictionary mapping file names to full paths
def read_dir(path):
    file_dict = {}
    files = os.listdir(path)
    for item in files:
        file_dict[item] = path + '/' + item
    return file_dict


def parse_local_fasta(data):
    genomes = {}
    genes = data.split('>')
    for gene in genes:
        if not gene:
            continue
        header, sequence = gene.split('\n', 1)
        sequence = sequence.replace('\n', '')  # removes newlines
        title, description = header.split('|')
        organism, locus = title.split('@')
        if organism in list(genomes.keys()):
            genomes[organism].add_gene(locus, sequence, description=description)
        else:
            genomes[organism] = Genome(organism)
            genomes[organism].add_gene(locus, sequence, description=description)
    return list(genomes.values())


# parses FASTA file from PATRIC server
def parse_patric_fasta(data):
    genome = {}
    genes = data.split('>')
    for gene in genes:
        if gene.count('\n') < 1:
            continue
        if not gene:
            continue
        header, sequence = gene.split('\n', 1)
        # process header
        header_segments = header.split('   ')   # sections are separated by groups of 3 spaces
        fig_id = ''.join(header_segments[0].split('|')[0:2])
        name = header_segments[1]
        sequence = sequence.replace('\n', '')
        genome[fig_id] = Gene(name=name, sequence=sequence, fig_id=fig_id)
    return genome


# reads a FASTA file and creates a list of Genome objects
def read_genomes(file_path):
    gene_file = open(file_path, 'r')
    data = gene_file.read()
    return parse_local_fasta(data)

# writes sequences to a FASTA file_path
def write_fasta(file_name, genes):
    fasta_file = open('temp_files/'+file_name, 'w')
    for name, seq in genes.items():
        fasta_file.write('>'+name+'\n')
        fasta_file.write(seq+'\n')
    fasta_file.close()

# reads the JSON file associated with a set of HMMs
def get_hmms(file_path):
    hmm_dict = {}
    for file_name in os.listdir(file_path):
        hmm_name = file_name.replace('.hmm', '')
        hmm_dict[hmm_name] = file_path + '/' + file_name

# compresses a single HMM file
def compress_hmm(hmm_name, file_path):
    shutil.copyfile(file_path, './temp_files/'+hmm_name)
    subprocess.call('hmmpress temp_files/%s' % hmm_name)

# compresses a set of HMMs
def compress_hmms(hmm_path):
    all_hmm = []
    for file_name in os.listdir(hmm_path):
        if '.hmm' in file_name:
            with open(hmm_path+'/'+file_name, 'r') as hmm_file:
                all_hmm.append(hmm_file.read())
    with open('temp_files/all', 'w') as all_hmm_file:  # creates a temporary file containing every hmm
        for hmm in all_hmm:
            all_hmm_file.write(hmm)
    subprocess.call('hmmpress temp_files/all', shell=True)

# searches for HMM files with outdated formats and converts them
def convert_old_hmms(path, latest_version):
    for file_name in os.listdir(path):
        if file_name[-4:] == '.hmm':  # checks for HMM fiels
            with open(path+'/'+file_name, 'r') as hmm_file:
                header = hmm_file.read().split('\n')[0]
                version = re.search('\[\S+', header).group(0).replace('[', '')
                if version != latest_version:
                    os.rename('%s/%s' % (path,file_name), '%s/%s_old' % (path,file_name))
                    subprocess.call('hmmconvert %s/%s_old > %s/%s' % (path,file_name,path,file_name), shell=True)
                    os.remove('%s/%s_old' % (path,file_name))

# read the output file for presence of file_name
def read_output(name):
    feature_dict = {}
    with open('temp_files/%s.out' % name) as output_file:
        segments = output_file.read().split('\n//')
        for block in segments:
            header = block.split('\n')[1]
            if 'Query' not in header:
                continue
            feature = block.split('\n')[1].split(':')[1].strip()
            feature = feature.split()[0]
            if 'No hits detected' in block:
                feature_dict[feature] = 0
            else:
                feature_dict[feature] = 1
    return feature_dict

# clear the temp_files folder
def clear_temp():
    for file_name in os.listdir('temp_files'):
        os.remove('temp_files/'+file_name)

# rescales PSSM file
def rescale_pssm(file_path):
    f = open(file_path, 'r')
    content = f.read()
    f.close()
    # modify contents
    start = content.find("scores {")
    end = content.find("}", start)
    scores = re.sub("([0-9]{2})(?=[\r\n\,])", "", content[start:end])
    scores = re.sub("\ (\-)?,", " 0,", scores)
    # rewrite file
    f = open(file_path, 'w')
    f.write(content[0:start] + scores + content[end:].replace("scalingFactor 100", "scalingFactor 1"))
    f.close()

# creates database for BLAST
def create_db(file_name):
    subprocess.run("makeblastdb -in temp_files/%s -dbtype prot" % file_name, shell=True)
