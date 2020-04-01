from django.urls import path
from finder.views import *

urlpatterns = [
    path('', start),
    path('id_search', id_search),
    path('show_genomes/<int:job_id>', show_genomes),
    path('select_method/<int:job_id>', select_method),
    path('wait_for_genomes/<str:task_id>', wait_for_genomes),
    path('motif_search/<int:job_id>', motif_search),
    path('hmm_search/<int:job_id>', hmm_search),
    path('pssm_search/<int:job_id>', pssm_search),
    path('run_search/<int:job_id>', run_search),
    path('export/<int:report_id>/', download),
    path('delete_motif/<int:search_id>', delete_motif),
    path('delete_hmm/<int:search_id>', delete_hmm),
    path('delete_pssm/<int:search_id>', delete_pssm)
]