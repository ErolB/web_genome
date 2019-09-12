from django.db import models


# organism genome
class GenomeModel(models.Model):
    organism = models.CharField(max_length=100)
    genome_id = models.CharField(max_length=100)


# protein-coding gene
class GeneModel(models.Model):
    name = models.CharField(max_length=200)
    sequence = models.CharField(max_length=10000)
    patric_id = models.CharField(max_length=300)
    fig_id = models.CharField(max_length=400)
    in_genome = models.ForeignKey(GenomeModel, on_delete=models.CASCADE)
    description = models.CharField(max_length=250)

# search method
class MotifSearchModel(models.Model):
    gene_name = models.CharField(max_length=100)
    motif_text = models.CharField(max_length=1000)


