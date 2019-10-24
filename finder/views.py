from django.shortcuts import render, redirect
from django.views.generic.edit import DeleteView
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django import forms
from celery.task.control import inspect

from finder.forms import *
from finder.models import *
from finder.tasks import *
from modules import retrieval
from modules import search_tools

import re
import json
import os
import random
import csv

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
        if genome_list == 'error':
            return HttpResponse('Cannot reach PATRIC. Try again later')
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
        HMMSearchModel.objects.all().delete()
        return redirect('/wait_for_genomes')


def wait_for_genomes(request):
    i = inspect()
    print(i)
    print(i.active())
    print(i.scheduled())
    active_tasks = list(i.active().values())[0]
    if active_tasks:
        #time.sleep(5)  # wait 10 seconds if there is an active task
        return render(request, 'waiting.html')
    else:
        return HttpResponseRedirect('/select_method')


def select_method(request):
    motif_searches = MotifSearchModel.objects.all()
    hmm_searches = HMMSearchModel.objects.all()
    return render(request, 'select_method.html', {'motif_searches': motif_searches, 'hmm_searches': hmm_searches})


def motif_search(request):
    if 'gene_name' in request.POST.keys():
        gene_name = request.POST['gene_name']
        motif_list = request.POST['motif_list']
        motif_search_entry = MotifSearchModel(gene_name=gene_name)
        motif_search_entry.save()
        for motif_text in motif_list.split('\n'):
            motif_text = motif_text.strip()
            if len(motif_text) == 0:
                continue  # skip blanks
            motif_entry = MotifModel(motif_text=motif_text, in_search=motif_search_entry)
            motif_entry.save()
        return redirect('/select_method')
    else:
        form = MotifSearchForm()
        return render(request, 'motif_search.html', {'form': form})


def hmm_search(request):
    if 'gene_name' in request.POST.keys():
        gene_name = request.POST['gene_name']
        hmm_file_obj = list(request.FILES.values())[0]
        file_name = 'hmms/%s.hmm' % gene_name
        with open(file_name, 'wb') as hmm_file:
            hmm_file.write(hmm_file_obj.read())
        threshold = float(request.POST['cutoff'])
        hmm_search_entry = HMMSearchModel(hmm_path=file_name, threshold=threshold, gene_name=gene_name)
        hmm_search_entry.save()
        return redirect('/select_method')
    else:
        form = HMMSearchForm()
        return render(request, 'hmm_search.html', {'form': form})


def run_search(request):
    all_genomes = GenomeModel.objects.all()
    all_motifs = MotifSearchModel.objects.all()
    all_hmms = HMMSearchModel.objects.all()
    genome_names = [item.organism for item in all_genomes]
    motif_names = [item.gene_name for item in all_motifs]
    results = []
    for genome in all_genomes:
        genome_result = {}
        genome_result['organism_name'] = genome.organism
        genome_result['genome_id'] = genome.genome_id
        relevant_genes = GeneModel.objects.filter(in_genome__genome_id=genome.genome_id)
        genome_result['motifs'] = []
        # process motif searches
        for motif in all_motifs:
            pattern_entries = MotifModel.objects.filter(in_search__gene_name=motif.gene_name)
            pattern_list = []
            for item in pattern_entries:
                pattern_list.append(search_tools.pattern_converter(item.motif_text))
            motif_entry = {'name': motif.gene_name, 'matches': []}
            for gene in relevant_genes:
                gene_found = True
                for pattern in pattern_list:
                    if not re.findall(pattern, gene.sequence):
                        gene_found = False
                        break
                if gene_found:
                    url = 'https://www.patricbrc.org/view/Feature/%s#view_tab=overview' % str(gene.patric_id)
                    motif_entry['matches'].append({'url': url, 'name': gene.name})
            genome_result['motifs'].append(motif_entry)
        # process HMM searches
        gene_dict = {gene.patric_id: gene.sequence for gene in relevant_genes}
        search_tools.write_fasta('temp_files/'+str(genome.genome_id), gene_dict)
        genome_result['hmms'] = []
        for hmm in all_hmms:
            hmm_entry = {'name': hmm.gene_name, 'matches': []}
            fig_ids = search_tools.hmm_scan('temp_files/'+str(genome.genome_id), hmm.hmm_path, hmm.threshold)
            print(fig_ids)
            for fig in fig_ids:
                url = 'https://www.patricbrc.org/view/Feature/%s#view_tab=overview' % str(fig)
                gene_name = [gene.name for gene in relevant_genes if gene.patric_id == fig][0]
                hmm_entry['matches'].append({'url': url, 'name': gene_name})
            genome_result['hmms'].append(hmm_entry)
        results.append(genome_result)
    headings = [motif.gene_name for motif in all_motifs]
    headings.extend([hmm.gene_name for hmm in all_hmms])
    # write report file (to be downloaded later)
    used_ids = os.listdir('reports/')
    report_id = str(random.randint(1000000, 9999999))
    while report_id in used_ids:  # this should be skipped in most cases
        report_id = str(random.randint(1000000, 9999999))
    with open('reports/%s.csv' % report_id, 'w') as report_file:
        hmm_names = [item.gene_name for item in all_hmms]
        motif_names = [item.gene_name for item in all_motifs]
        column_names = ['organism'] + hmm_names + motif_names
        writer = csv.DictWriter(fieldnames=column_names, f=report_file)
        writer.writeheader()
        for genome_entry in results:
            new_row = {'organism': genome_entry['organism_name']}
            for motif_entry in genome_entry['motifs']:
                url_list = ' / '.join([item['url'] for item in motif_entry['matches']])
                new_row[motif_entry['name']] = url_list
            for hmm_entry in genome_entry['hmms']:
                url_list = ' / '.join([item['url'] for item in hmm_entry['matches']])
                new_row[hmm_entry['name']] = url_list
            writer.writerow(new_row)

    return render(request, 'result_page.html', {'results': results, 'headings': headings, 'report': int(report_id)})


def download(request, report_id):
    with open('reports/%s.csv' % report_id, 'r') as report_file:
        response = HttpResponse(report_file.read(), content_type="application/vnd.ms-excel")
    return response


class DeleteMotif(DeleteView):
    model = MotifSearchModel
    success_url = '/select_method'


class DeleteHMM(DeleteView):
    model = HMMSearchModel
    success_url = '/select_method'
