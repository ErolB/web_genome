from django import forms

class IdSearch(forms.Form):
    id_list = forms.CharField(widget=forms.Textarea, label='')

class MotifSearchForm(forms.Form):
    gene_name = forms.CharField(label='Enter Gene Name')
    motif = forms.CharField(label='Enter Motif Pattern')