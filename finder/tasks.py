from celery.decorators import task
from celery.utils.log import get_task_logger
from modules import retrieval

from . models import *


@task(name='loading')
def create_genomes(approved_genomes):
    genome_objs = retrieval.retrieve_sequences(approved_genomes)
    for genome in genome_objs:
        genome_entry = GenomeModel(organism=genome.organism, genome_id=genome.id)
        genome_entry.save()
        for gene in genome.genes.values():
            gene_entry = GeneModel(name=gene.name, sequence=gene.sequence, in_genome=genome_entry, patric_id=gene.patric_id)
            gene_entry.save()