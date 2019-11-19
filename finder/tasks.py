from celery import shared_task
from celery.utils.log import get_task_logger
from modules import retrieval
from finder.models import *
import datetime


@shared_task
def create_genomes(approved_genomes, job_id):
    genome_objs = retrieval.retrieve_sequences(approved_genomes)
    for genome in genome_objs:
        current_genomes = GenomeModel.objects.all()  # load list of genomes in storage
        current_genome_ids = [item.genome_id for item in current_genomes]
        if genome.id not in current_genome_ids:
            genome_entry = GenomeModel(organism=genome.organism, genome_id=genome.id)
            genome_entry.save()
            for gene in genome.genes.values():
                gene_entry = GeneModel(name=gene.name, sequence=gene.sequence, in_genome=genome_entry, patric_id=gene.patric_id)
                gene_entry.save()
        # add entry to genome usage table
        tracker_entry = GenomeUse(genome_id=genome.id, last_used=datetime.datetime.now(), job_id=job_id)
        tracker_entry.save()
