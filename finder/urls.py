from django.urls import path
from . views import *

urlpatterns = [
    path('', start),
    path('id_search', id_search),
    path('show_genomes', show_genomes),
    path('select_method', select_method),
    path('motif_search', motif_search),
    path('run_search', run_search)
]