import subprocess
import os
import re

from modules import utils, file_tools

class HMMSearch(object):
    def __init__(self, file_name):
        self.file = file_name
        self.name = file_name.split('/')[-1]
        self.threshold = 0.000001

    def set_threshold(self, new_value):
        self.threshold = new_value

    def run(self, genome):
        file_tools.write_fasta(genome.organism, genome.get_genes())  # write temporary file
        features = hmm_scan(genome.organism, self.file, threshold=self.threshold)
        return features

class MotifSearch(object):
    def __init__(self, motif_file):
        input_motifs = open(motif_file, 'r').readlines()
        self.motif_dict = {motif: pattern_converter(motif) for motif in input_motifs}
        self.name = motif_file.split('/')[-1]
        self.threshold = None

    def run(self, genome):
        features = motif_scan_genome(genome, self.motif_dict.values())
        return features

class PSIBlastSearch(object):
    def __init__(self, pssm_file):
        self.pssm_file = pssm_file
        self.name = pssm_file.split('/')[-1]
        self.threshold = 0.000001

    def set_threshold(self, new_value):
        self.threshold = new_value

    def run(self, genome):
        features = search_msa(genome.organism, self.pssm_file, threshold=self.threshold)
        return features

# parses HMMER output
def hmmer_parse(text):
    if 'No hits detected' in text:
        return []
    else:
        lines = text.split('\n')
        identifiers = [item[3:].strip() for item in lines if '>>' in item]
        return identifiers

# scans using HMMs
def hmm_scan(genome_name, hmm_name, threshold=0.000001):
    feature_list = []
    os.chdir('temp_files')
    process = subprocess.run('hmmsearch -E %s %s %s' % (str(threshold), hmm_name, genome_name),
        stdout=subprocess.PIPE, shell=True)  # E-value cutoff is 10^-6
    os.chdir('..')
    block = process.stdout.decode()
    results = hmmer_parse(block)
    return results

# parses PSI-BLAST output
def psiblast_parse(text):
    identifiers = []
    lines = text.split('\n')
    for line in lines:
        if len(line) < 1:
            continue
        if line[0] == '>':
            identifiers.append(line[1:].strip())
    return identifiers

# scans using PSI-BLAST
def search_msa(genome_name, msa_path, threshold=0.000001):
    process1 = subprocess.run('makeblastdb -in temp_files/%s -dbtype prot -out temp_files/%s' %
        (genome_name, genome_name), stdout=subprocess.PIPE, shell=True)
    process2 = subprocess.run('psiblast -db temp_files/%s -in_msa %s -evalue %s' %
        (genome_name,msa_path,str(threshold)), stdout=subprocess.PIPE, shell=True)
    output = process2.stdout.decode()
    return psiblast_parse(output)

# converts a pattern in PROSITE format to standard regualar expression format
def pattern_converter(prosite_pattern):
    segments = prosite_pattern.split('-')
    output_pattern = ''
    for item in segments:
        # handle a set of possible values
        possible_chars = re.findall('\[\w+\]', item)
        excluded_chars = re.findall('\{\w+\}', item)
        if possible_chars:
            possible_chars = re.sub('(\[|\])', '', possible_chars[0])
            aa_list = [aa for aa in possible_chars]
            output_pattern += ('(' + '|'.join(aa_list) + ')')
        # handle a set of excluded values
        elif excluded_chars:
            excluded_chars = re.sub('(\{|\})', '', excluded_chars[0])
            aa_list = [aa for aa in excluded_chars]
            output_pattern += '[^(' + '|'.join(aa_list) + ')]'
        # handle single values
        else:
            aa = re.findall('(?=\(?)\w', item)[0]
            if aa == 'x':  # check for wildcarda
                output_pattern += "\w"
            else:
                output_pattern += aa
        # handle multiplier
        multiplier = re.findall('\(\d\-?\d?\)', item)
        if multiplier:
            multiplier = re.sub('(\(|\))', '', multiplier[0])
            output_pattern += '{' + multiplier + '}'
    return output_pattern

def motif_scan_genome(genome_obj, patterns):
    features = []
    for gene in genome_obj.genes.values():
        include = True
        for motif in patterns:
            seq = gene.get_sequence()
            if not re.findall(motif, seq):
                include = False
                break
        if include:
            features.append(gene.name)
    return features