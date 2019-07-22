from django.shortcuts import render, redirect
from django.views.generic.edit import DeleteView
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django import forms
from celery.task.control import inspect

from . forms import *
from . models import *
from . tasks import *
from modules import retrieval
from modules import search_tools

import re
import json
import time
import multiprocessing

genome_load_process = []

def start(request):
    start_page = loader.get_template('start.html')
    return HttpResponse(start_page.render({}, request))


def id_search(request):
    # ensure that database is clear (not ideal for multiple users)
    GeneModel.objects.all().delete()
    GenomeModel.objects.all().delete()
    # generate page
    form = IdSearch()
    return render(request, 'id_search.html', {'form': form})


def show_genomes(request):
    print(request.POST)
    if 'id_list' in request.POST.keys():
        id_list_string = request.POST['id_list']
        print(id_list_string)
        # parse text from form
        id_list = re.split(',|\s', id_list_string)
        temp = []
        for item in id_list:
            processed_item = re.sub('\s', '', item)
            if processed_item:
                temp.append(item)
        id_list = temp
        # get genomes from PATRIC
        genome_list = retrieval.search_by_ids(id_list)
        # render page
        genome_info = {genome.id: {'id': genome.id, 'name': genome.organism} for genome in genome_list}
        genome_text =[(json.dumps(genome_info[genome.id]), '%s (%s)' % (genome.organism, genome.id)) for genome in genome_list]
        #### I know this should not be defined here. If you know a better way, feel free to fix it ####
        class VerifyGenomes(forms.Form):
            genomes = forms.MultipleChoiceField(help_text='Select genomes to keep',
                                                choices=genome_text,
                                                widget=forms.CheckboxSelectMultiple(attrs={'inline': True}),
                                                )
        form = VerifyGenomes()
        return render(request, 'show_genomes.html', {'form': form})
    elif 'genomes' in request.POST.keys():
        print('got these...')
        results = [*request.POST.lists()]
        print(results)
        approved_genomes = []
        for pair in results:
            if pair[0] == 'genomes':
                approved_genomes = pair[1]
        print(approved_genomes)
        # call Celery task
        create_genomes.delay(approved_genomes)
        MotifSearchModel.objects.all().delete()
        return redirect('/wait_for_genomes')


def wait_for_genomes(request):
    i = inspect()
    time.sleep(0.5)
    print(i.active())
    active_tasks = list(i.active().values())[0]
    if active_tasks:
        #time.sleep(5)  # wait 10 seconds if there is an active task
        return render(request, 'waiting.html')
    else:
        return HttpResponseRedirect('/select_method')


def select_method(request):
    motif_searches = MotifSearchModel.objects.all()
    return render(request, 'select_method.html', {'motif_searches': motif_searches})


def motif_search(request):
    if 'gene_name' in request.POST.keys():
        gene_name = request.POST['gene_name']
        motif = request.POST['motif']
        motif_entry = MotifSearchModel(gene_name=gene_name, motif_text=motif)
        motif_entry.save()
        return redirect('/select_method')
    else:
        form = MotifSearchForm()
        return render(request, 'motif_search.html', {'form': form})

def run_search(request):
    all_genomes = GenomeModel.objects.all()
    all_motifs = MotifSearchModel.objects.all()
    genome_names = [item.organism for item in all_genomes]
    motif_names = [item.gene_name for item in all_motifs]
    results = []
    for genome in all_genomes:
        genome_result = {}
        genome_result['organism_name'] = genome.organism
        genome_result['genome_id'] = genome.genome_id
        relevant_genes = GeneModel.objects.filter(in_genome__genome_id=genome.genome_id)
        genome_result['motifs'] = []
        for motif in all_motifs:
            pattern = search_tools.pattern_converter(motif.motif_text)
            motif_entry = {'name': motif.gene_name, 'matches': []}
            for gene in relevant_genes:
                if re.findall(pattern, gene.sequence):
                    url = 'https://www.patricbrc.org/view/Feature/%s#view_tab=overview' % str(gene.patric_id)
                    print(url)
                    motif_entry['matches'].append({'url': url, 'name': gene.name})
            genome_result['motifs'].append(motif_entry)
        results.append(genome_result)
    print('here')
    print(results)
    headings = [motif.gene_name for motif in all_motifs]
    return render(request, 'result_page.html', {'results': results, 'headings': headings})


class DeleteMotif(DeleteView):
    model = MotifSearchModel
    success_url = '/select_method'