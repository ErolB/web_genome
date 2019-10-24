from django.urls import path
from finder.views import *

urlpatterns = [
    path('', start),
    path('id_search', id_search),
    path('show_genomes', show_genomes),
    path('select_method', select_method),
    path('wait_for_genomes', wait_for_genomes),
    path('motif_search', motif_search),
    path('hmm_search', hmm_search),
    path('run_search', run_search),
    path('export/<int:report_id>/', download),
    path('delete_m/<int:pk>', DeleteMotif.as_view(), name='delete_motif'),
    path('delete_h/<int:pk>', DeleteHMM.as_view(), name='delete_hmm')
]