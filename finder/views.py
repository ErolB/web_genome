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
    # create new job
    job = JobModel()
    job.save()
    job_id = job.job_id
    print(job.start_time)
    # generate page
    form = IdSearch()
    return render(request, 'id_search.html', {'form': form, 'job_id': job_id})


def show_genomes(request, job_id):
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
            genomes = forms.MultipleChoiceField(
                                                help_text='Select genomes to keep',
                                                choices=genome_text,
                                                widget=forms.CheckboxSelectMultiple(attrs={'inline': True, 'checked': True}),
                                                initial={'choices': genome_text}
                                                )
        form = VerifyGenomes()
        return render(request, 'show_genomes.html', {'form': form, 'job_id': job_id})
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
        task_id = create_genomes.delay(approved_genomes, job_id).id
        current_job = JobModel.objects.get(job_id=job_id)
        task = TaskModel(task_id=str(task_id), job=current_job)
        task.save()
        return redirect('/wait_for_genomes/%s' % str(task_id))


def wait_for_genomes(request, task_id):
    i = inspect()
    print(i)
    print(i.active())
    print(i.scheduled())
    active_tasks = list(i.active().values())[0]
    if active_tasks:
        #time.sleep(5)  # wait 10 seconds if there is an active task
        return render(request, 'waiting.html')
    else:
        # retrieve current job ID
        current_task = TaskModel.objects.get(task_id=task_id)
        job_id = current_task.job.job_id
        return HttpResponseRedirect('/select_method/%s' % job_id)


def select_method(request, job_id):
    motif_searches = MotifSearchModel.objects.filter(job__job_id=job_id)
    hmm_searches = HMMSearchModel.objects.filter(job__job_id=job_id)
    pssm_searches = PSSMSearchModel.objects.filter(job__job_id=job_id)
    return render(request, 'select_method.html', {'motif_searches': motif_searches, 'job_id': job_id,
                                                  'hmm_searches': hmm_searches, 'pssm_searches': pssm_searches})


def motif_search(request, job_id):
    if 'gene_name' in request.POST.keys():
        current_job = JobModel.objects.get(job_id=job_id)
        gene_name = request.POST['gene_name']
        motif_list = request.POST['motif_list']
        motif_search_entry = MotifSearchModel(gene_name=gene_name, job=current_job)
        motif_search_entry.save()
        for motif_text in motif_list.split('\n'):
            motif_text = motif_text.strip()
            if len(motif_text) == 0:
                continue  # skip blanks
            motif_entry = MotifModel(motif_text=motif_text, in_search=motif_search_entry)
            motif_entry.save()
        return redirect('/select_method/%s' % job_id)
    else:
        form = MotifSearchForm()
        return render(request, 'motif_search.html', {'form': form, 'job_id': job_id})


def hmm_search(request, job_id):
    if 'gene_name' in request.POST.keys():
        gene_name = request.POST['gene_name']
        hmm_file_obj = list(request.FILES.values())[0]
        file_name = 'hmms/%s.hmm' % gene_name
        with open(file_name, 'wb') as hmm_file:
            hmm_file.write(hmm_file_obj.read())
        threshold = float(request.POST['cutoff'])
        current_job = JobModel.objects.get(job_id=job_id)
        hmm_search_entry = HMMSearchModel(hmm_path=file_name, threshold=threshold, gene_name=gene_name, job=current_job)
        hmm_search_entry.save()
        return redirect('/select_method/%s' % job_id)
    else:
        form = HMMSearchForm()
        return render(request, 'hmm_search.html', {'form': form, 'job_id': job_id})


def pssm_search(request, job_id):
    if 'gene_name' in request.POST.keys():
        gene_name = request.POST['gene_name']
        pssm_file_obj = list(request.FILES.values())[0]
        file_name = 'pssms/%s.txt' % gene_name
        with open(file_name, 'wb') as pssm_file:
            pssm_file.write(pssm_file_obj.read())
        threshold = float(request.POST['cutoff'])
        current_job = JobModel.objects.get(job_id=job_id)
        pssm_search_entry = PSSMSearchModel(pssm_path=file_name, threshold=threshold, gene_name=gene_name, job=current_job)
        pssm_search_entry.save()
        return redirect('/select_method/%s' % job_id)
    else:
        form = PSSMSearchForm()
        return render(request, 'pssm_search.html', {'form': form, 'job_id': job_id})


def run_search(request, job_id):
    all_genome_entries = GenomeUse.objects.filter(job_id=job_id).values()
    all_motifs = MotifSearchModel.objects.filter(job__job_id=job_id)
    all_hmms = HMMSearchModel.objects.filter(job__job_id=job_id)
    all_pssms = PSSMSearchModel.objects.filter(job__job_id=job_id)
    # retrieve genome objects
    all_genomes = []
    genome_ids = [item['genome_id'] for item in all_genome_entries]
    all_genomes = [GenomeModel.objects.get(genome_id=item) for item in genome_ids]
    # run searches
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
        # process PSSM searches
        genome_result['pssms'] = []
        for pssm in all_pssms:
            pssm_entry = {'name': pssm.gene_name, 'matches': []}
            fig_ids = search_tools.search_msa(genome.genome_id, pssm.pssm_path, threshold=pssm.threshold)
            for fig in fig_ids:
                url = 'https://www.patricbrc.org/view/Feature/%s#view_tab=overview' % str(fig)
                gene_name = [gene.name for gene in relevant_genes if gene.patric_id == fig][0]
                pssm_entry['matches'].append({'url': url, 'name': gene_name})
            genome_result['pssms'].append(pssm_entry)
        results.append(genome_result)
    headings = [motif.gene_name for motif in all_motifs]
    headings.extend([hmm.gene_name for hmm in all_hmms])
    headings.extend([pssm.gene_name for pssm in all_pssms])
    # write report file (to be downloaded later)
    used_ids = os.listdir('reports/')
    report_id = str(random.randint(1000000, 9999999))
    while report_id in used_ids:  # this should be skipped in most cases
        report_id = str(random.randint(1000000, 9999999))
    with open('reports/%s.csv' % report_id, 'w') as report_file:
        hmm_names = [item.gene_name for item in all_hmms]
        motif_names = [item.gene_name for item in all_motifs]
        pssm_names = [item.gene_name for item in all_pssms]
        column_names = ['organism'] + hmm_names + motif_names + pssm_names
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
            for pssm_entry in genome_entry['pssms']:
                url_list = ' / '.join([item['url'] for item in pssm_entry['matches']])
                new_row[pssm_entry['name']] = url_list
            writer.writerow(new_row)

    return render(request, 'result_page.html', {'results': results, 'headings': headings, 'report': int(report_id)})


def download(request, report_id):
    with open('reports/%s.csv' % report_id, 'r') as report_file:
        response = HttpResponse(report_file.read(), content_type="application/vnd.ms-excel")
    return response

def delete_motif(request, search_id):
    current_search = MotifSearchModel.objects.get(id=search_id)
    current_job = current_search.job.job_id
    current_search.delete()
    motif_searches = MotifSearchModel.objects.filter(job__job_id=current_job)
    hmm_searches = HMMSearchModel.objects.filter(job__job_id=current_job)
    pssm_searches = PSSMSearchModel.objects.filter(job__job_id=current_job)
    return render(request, 'select_method.html', {'motif_searches': motif_searches, 'job_id': current_job,
                                                  'hmm_searches': hmm_searches, 'pssm_searches': pssm_searches})

def delete_hmm(request, search_id):
    current_search = HMMSearchModel.objects.get(id=search_id)
    current_job = current_search.job.job_id
    current_search.delete()
    motif_searches = MotifSearchModel.objects.filter(job__job_id=current_job)
    hmm_searches = HMMSearchModel.objects.filter(job__job_id=current_job)
    pssm_searches = PSSMSearchModel.objects.filter(job__job_id=current_job)
    return render(request, 'select_method.html', {'motif_searches': motif_searches, 'job_id': current_job,
                                                  'hmm_searches': hmm_searches, 'pssm_searches': pssm_searches})

def delete_pssm(request, search_id):
    current_search = PSSMSearchModel.objects.get(id=search_id)
    current_job = current_search.job.job_id
    current_search.delete()
    motif_searches = MotifSearchModel.objects.filter(job__job_id=current_job)
    hmm_searches = HMMSearchModel.objects.filter(job__job_id=current_job)
    pssm_searches = PSSMSearchModel.objects.filter(job__job_id=current_job)
    return render(request, 'select_method.html', {'motif_searches': motif_searches, 'job_id': current_job,
                                                  'hmm_searches': hmm_searches, 'pssm_searches': pssm_searches})

