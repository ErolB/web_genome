class Gene(object):
    def __init__(self, name, sequence, description=None, patric_id=None, fig_id=None):
        self.name = name
        self.sequence = sequence
        self.description = description
        self.patric_id = patric_id
        if fig_id:
            self.fig_id = fig_id
        else:
            self.fig_id = 'not available'

    def __str__(self):
        return '%s (%s)' % (self.name, self.patric_id)

    def get_name(self):
        return self.name

    def get_sequence(self):
        return self.sequence

class Genome(object):
    def __init__(self, organism, id=None):
        self.organism = organism.replace(' ', '_')
        self.id = id
        self.genes = {}

    def add_gene(self, name, sequence, description=None, patric_id=None):
        self.genes[name] = Gene(name, sequence, description=description, patric_id=patric_id)

    def add_gene_obj(self, gene_id, obj):
        self.genes[gene_id] = obj

    def get_sequence(self, name):
        return self.genes[name].get_sequence()

    # returns a list of sequences
    def get_all_sequences(self):
        return [gene.get_sequence() for gene in self.genes.values()]

    # returns a dictionary mapping gene names to sequences
    def get_genes(self):
         gene_dict = {}
         for gene in self.genes.items():
             name = gene[0]
             seq = gene[1].get_sequence()
             gene_dict[name] = seq
         return gene_dict


