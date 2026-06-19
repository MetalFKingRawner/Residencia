from django import forms

class SolicitudAccesoForm(forms.Form):
    nombre = forms.CharField(max_length=100, label='Nombre completo')
    email = forms.EmailField(label='Correo electrónico')
    telefono = forms.CharField(max_length=20, required=False, label='Teléfono')
    mensaje = forms.CharField(widget=forms.Textarea, required=False, label='Mensaje adicional')