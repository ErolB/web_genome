from django import forms

class IdSearch(forms.Form):
    id_list = forms.CharField(widget=forms.Textarea, label='')

class MotifSearchForm(forms.Form):
    gene_name = forms.CharField(label='Enter Gene Name')
    motif_list = forms.CharField(widget=forms.Textarea, label='Enter Motif Patterns (one per line)')

class HMMSearchForm(forms.Form):
    gene_name = forms.CharField(label='Enter Gene Name')
    hmm_file = forms.FileField(label='Upload HMM File')
    cutoff = forms.FloatField(label='Enter E-value cutoff', initial=0.000001)

class PSSMSearchForm(forms.Form):
    gene_name = forms.CharField(label='Enter Gene Name')
    pssm_file = forms.FileField(label='Upload PSSM File')
    cutoff = forms.FloatField(label='Enter E-value cutoff', initial=0.000001)
