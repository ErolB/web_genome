from django.urls import path
from finder.views import *

urlpatterns = [
    path('', start),
    path('id_search', id_search),
    path('show_genomes', show_genomes),
    path('select_method', select_method),
    path('wait_for_genomes', wait_for_genomes),
    path('motif_search', motif_search),
    path('run_search', run_search),
    path('delete_m/<int:pk>', DeleteMotif.as_view(), name='delete_motif')
]