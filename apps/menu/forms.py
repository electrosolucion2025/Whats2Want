from django import forms

class MenuUploadForm(forms.Form):
    tenant = forms.CharField(label="Tenant ID", max_length=50, required=True)
    file = forms.FileField(label="Subir archivo JSON")
