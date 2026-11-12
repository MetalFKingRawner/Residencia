# landing/forms.py
from django import forms

class ContactoForm(forms.Form):
    nombre = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    telefono = forms.CharField(max_length=20, required=False)
    servicio = forms.CharField(max_length=100, required=False)
    mensaje = forms.CharField(widget=forms.Textarea, required=True)
