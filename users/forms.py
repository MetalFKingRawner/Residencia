# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    # Campos personalizados con estilos y validación
    username = forms.CharField(
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: juan_perez'
        }),
        help_text="Requerido. 150 caracteres o menos. Letras, dígitos y @/./+/-/_ solamente."
    )
    
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: juan@ejemplo.com'
        })
    )
    
    full_name = forms.CharField(
        label="Nombre completo",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Juan Pérez López'
        })
    )
    
    date_of_birth = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
        ('N', 'Prefiero no decir'),
    ]
    
    gender = forms.ChoiceField(
        label="Género",
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='N'
    )
    
    institution = forms.CharField(
        label="Institución/Empresa",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Universidad XYZ'
        })
    )
    
    education_level = forms.CharField(
        label="Nivel de estudios",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Licenciatura'
        })
    )
    
    occupation = forms.CharField(
        label="Ocupación",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Ingeniero Civil'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + (
            'email',
            'full_name',
            'date_of_birth',
            'gender',
            'institution',
            'education_level',
            'occupation'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar mensajes de ayuda y estilos de campos base
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].help_text = """
            Mínimo 8 caracteres.<br>
            No puede ser similar a tu información personal.<br>
            No puede ser una contraseña común.<br>
            No puede ser completamente numérica.
        """
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        if commit:
            user.save()
        return user
    
class CustomUserChangeForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date', 
                'class': 'form-control'
            },
            format='%Y-%m-%d'
        ),
        required=False
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'full_name', 
            'email', 
            'date_of_birth', 
            'gender', 
            'institution', 
            'education_level', 
            'occupation'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'education_level': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que la fecha esté en formato ISO (YYYY-MM-DD)
        if self.instance.date_of_birth:
            self.initial['date_of_birth'] = self.instance.date_of_birth.isoformat()