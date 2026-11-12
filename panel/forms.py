# panel/forms.py
import time

from django import forms
from django.forms import inlineformset_factory
from courses.models import Curso, Inscripcion, Leccion, RecursoLeccion
from users.models import CustomUser
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group

GRUPO_DIRECTIVO = 'Directivo / Coordinador'
GRUPO_INSTRUCTORES = 'Instructores'

ROL_CHOICES = [
    ('estudiante', 'Estudiante / Aplicante'),
    ('instructor', 'Psicólogo / Instructor'),
    ('directivo', 'Directivo / Coordinador'),
    ('sistema', 'Administrador del Sistema'),
]


class CursoForm(forms.ModelForm):
    """
    Formulario para crear/editar cursos.
    Incluye validación: no publicar si no tiene lecciones.
    """
    class Meta:
        model = Curso
        fields = ['titulo', 'descripcion', 'imagen', 'instructor', 'publicado']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'imagen': forms.FileInput(),   # ← agrega esta línea
        }

    def clean(self):
        cleaned_data = super().clean()
        publicado = cleaned_data.get('publicado')
        # Si se intenta publicar, validamos que tenga al menos una lección
        if publicado:
            # Si es un formulario de edición, podemos obtener la instancia
            if self.instance and self.instance.pk:
                lecciones_count = self.instance.lecciones.count()
            else:
                # Si es nuevo, aún no hay lecciones, pero el formset se validará aparte
                # Este método se ejecuta antes de que el formset se guarde, así que
                # no podemos contar aún. Delegaremos la validación a la vista.
                pass
        return cleaned_data


class LeccionForm(forms.ModelForm):
    """
    Formulario para lecciones dentro del formset.
    """
    class Meta:
        model = Leccion
        fields = ['titulo', 'orden', 'vista_previa_gratis']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos el campo 'orden' requerido y con un valor por defecto
        self.fields['orden'].required = True


# Creamos el formset para Leccion, que se usará dentro del formulario de Curso
CursoLeccionFormSet = inlineformset_factory(
    Curso,
    Leccion,
    form=LeccionForm,
    extra=1,           # Una fila vacía por defecto
    can_delete=True,   # Permite eliminar lecciones
    min_num=0,
    validate_min=False,
)

RecursoFormSet = inlineformset_factory(
    Leccion,
    RecursoLeccion,
    fields=['tipo', 'orden', 'contenido_texto', 'video_url', 'archivo'],
    extra=1,
    can_delete=True,
    widgets={
        # CORRECCIÓN: se eliminó el widget Textarea de contenido_texto
        # para que Django use el CKEditorWidget definido en el RichTextField del modelo.
        # Si se sobreescribe aquí con Textarea, CKEditor nunca se activa.
        'tipo': forms.Select(attrs={'class': 'form-control'}),
        'orden': forms.NumberInput(attrs={'class': 'form-control'}),
        'video_url': forms.URLInput(attrs={'class': 'form-control'}),
        'archivo': forms.FileInput(attrs={'class': 'form-control'}),
    }
)

class InscripcionForm(forms.ModelForm):
    """
    Formulario para inscribir manualmente a un usuario en un curso.
    """
    class Meta:
        model = Inscripcion
        fields = ['estudiante', 'curso', 'progreso', 'completado', 'certificado_generado']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-control'}),
            'progreso': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'completado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'certificado_generado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar los selects alfabéticamente
        self.fields['estudiante'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')
        self.fields['curso'].queryset = Curso.objects.filter(publicado=True).order_by('titulo')
        # Hacer que el progreso sea 0 por defecto
        if not self.instance.pk:
            self.fields['progreso'].initial = 0
            self.fields['completado'].initial = False
            self.fields['certificado_generado'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        estudiante = cleaned_data.get('estudiante')
        curso = cleaned_data.get('curso')
        completado = cleaned_data.get('completado')
        progreso = cleaned_data.get('progreso', 0)
        
        # Validar que no exista una inscripción duplicada
        if estudiante and curso:
            if Inscripcion.objects.filter(estudiante=estudiante, curso=curso).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(
                    f"El usuario {estudiante.username} ya está inscrito en el curso {curso.titulo}"
                )
        
        # Si está marcado como completado, el progreso debe ser 100%
        if completado and progreso < 100:
            raise forms.ValidationError(
                "Si el curso está completado, el progreso debe ser 100%"
            )
        
        # Si el progreso es 100%, marcar como completado automáticamente
        if progreso == 100 and not completado:
            cleaned_data['completado'] = True
        
        return cleaned_data
    
class EstudianteRapidoForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Nombre completo",
        widget=forms.TextInput(attrs={
            'class': 'il-form-control',
            'placeholder': 'Ej: Juan Pérez López',
        })
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'il-form-control',
            'placeholder': 'Ej: juan@ejemplo.com',
        })
    )
 
    class Meta:
        model = CustomUser
        fields = ['full_name', 'email']
 
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

class CustomUserCreationForm(forms.ModelForm):
    """
    Formulario completo para crear usuarios desde el panel.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Dejar en blanco para generar automáticamente"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label="Confirmar contraseña"
    )
    # ── NUEVO CAMPO DE ROL ──
    rol = forms.ChoiceField(
        choices=ROL_CHOICES,
        required=True,
        initial='estudiante',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = CustomUser
        # Quitamos 'is_staff' y agregamos 'rol'
        fields = [
            'username', 'email', 'full_name', 'date_of_birth', 'gender', 
            'institution', 'education_level', 'occupation', 'rol', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Institución/Empresa'}),
            'education_level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nivel de estudios'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ocupación'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.data.get('username'):
            self.fields['username'].initial = 'usuario_' + str(int(time.time()))[-6:]
        self.fields['full_name'].required = True
        self.fields['email'].required = True
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError("El nombre de usuario es obligatorio")
        if CustomUser.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este nombre de usuario ya está en uso")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("El correo electrónico es obligatorio")
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este correo electrónico ya está registrado")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and password != confirm_password:
            raise ValidationError("Las contraseñas no coinciden")
        if password and len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        rol = self.cleaned_data.get('rol')

        if password:
            user.set_password(password)

        # ── LÓGICA DEL ROL ──
        # 'sistema' es la única opción que otorga is_staff (acceso a los mixins
        # del panel y, si además se marca is_superuser manualmente, al /admin/).
        # Ese is_superuser NO se gestiona aquí a propósito, ver nota en la conversación.
        user.is_staff = (rol == 'sistema')

        if commit:
            user.save()
            # Limpiamos grupos anteriores y asignamos el nuevo
            user.groups.clear()
            if rol == 'directivo':
                grupo, _ = Group.objects.get_or_create(name=GRUPO_DIRECTIVO)
                user.groups.add(grupo)
            elif rol == 'instructor':
                grupo, _ = Group.objects.get_or_create(name=GRUPO_INSTRUCTORES)
                user.groups.add(grupo)
            # 'sistema' -> ya tiene acceso total vía is_staff, no necesita grupo.
            # 'estudiante' -> caso base, sin grupo.

        return user


class CustomUserChangeForm(forms.ModelForm):
    """
    Formulario para editar usuarios existentes.
    """
    # ── NUEVO CAMPO DE ROL ──
    rol = forms.ChoiceField(
        choices=ROL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'full_name', 'date_of_birth', 'gender', 
            'institution', 'education_level', 'occupation', 'rol', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'education_level': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = "El nombre de usuario no se puede cambiar"
        self.fields['date_of_birth'].widget.attrs['value'] = self.instance.date_of_birth.isoformat() if self.instance.date_of_birth else ''
        
        # ── LEER EL ROL ACTUAL DE LA BASE DE DATOS ──
        if self.instance.pk:
            if self.instance.is_staff:
                self.fields['rol'].initial = 'sistema'
            elif self.instance.groups.filter(name=GRUPO_DIRECTIVO).exists():
                self.fields['rol'].initial = 'directivo'
            elif self.instance.groups.filter(name=GRUPO_INSTRUCTORES).exists():
                self.fields['rol'].initial = 'instructor'
            else:
                self.fields['rol'].initial = 'estudiante'
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este nombre de usuario ya está en uso")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este correo electrónico ya está registrado")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        rol = self.cleaned_data.get('rol')

        # ── LÓGICA DEL ROL ──
        user.is_staff = (rol == 'sistema')

        if commit:
            user.save()
            user.groups.clear()
            if rol == 'directivo':
                grupo, _ = Group.objects.get_or_create(name=GRUPO_DIRECTIVO)
                user.groups.add(grupo)
            elif rol == 'instructor':
                grupo, _ = Group.objects.get_or_create(name=GRUPO_INSTRUCTORES)
                user.groups.add(grupo)

        return user


class UsuarioFiltroForm(forms.Form):
    """
    Formulario para filtrar usuarios en el listado.
    """
    busqueda = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Buscar por nombre, email o username...'
        })
    )
    rol = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('sistema', 'Administrador del Sistema'),
            ('directivo', 'Directivo / Coordinador'),
            ('instructor', 'Psicólogo / Instructor'),
            ('estudiante', 'Estudiante / Aplicante'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    activo = forms.ChoiceField(
        required=False, 
        choices=[
            ('', 'Todos'),
            ('si', 'Activos'),
            ('no', 'Inactivos'),
        ], 
        widget=forms.Select(attrs={'class': 'form-select'})
    )