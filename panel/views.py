# panel/views.py
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.core.exceptions import PermissionDenied

from psycho_platform import settings
from users.models import CustomUser

from .mixins import (
    StaffRequiredMixin,
    AdminOrStaffRequiredMixin,
    InstructorGroupRequiredMixin,
    InstructorOrStaffMixin,
    CursoPermissionMixin,
    InstructorCanViewInscripcionesMixin,
)
from .forms import CursoForm, CursoLeccionFormSet
from courses.models import Curso, Leccion, RecursoLeccion, Inscripcion
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import LeccionForm, RecursoFormSet, InscripcionForm, EstudianteRapidoForm
from django.db.models import Q

import json
from django.http import HttpResponse, JsonResponse
from django.views import View
from .utils import generar_username, generar_password_temporal
from .forms import CustomUserCreationForm, CustomUserChangeForm, UsuarioFiltroForm


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _form_errors_dict(form):
    return {field: [str(e) for e in errs] for field, errs in form.errors.items()}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

from django.core.exceptions import PermissionDenied  # Asegúrate de tener esta importación arriba

def dashboard(request):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
 
    user = request.user
 
    es_admin = user.is_staff or user.groups.filter(name='Directivo / Coordinador').exists()
    es_instructor = user.groups.filter(name='Instructores').exists()
 
    if not es_admin and not es_instructor:
        raise PermissionDenied("No tienes permisos para acceder al panel.")
 
    if es_admin:
        cursos_qs = Curso.objects.all()
    else:
        cursos_qs = Curso.objects.filter(instructor=user)
 
    total_cursos = cursos_qs.count()
    cursos_publicados = cursos_qs.filter(publicado=True).count()
    total_lecciones = Leccion.objects.filter(curso__in=cursos_qs).count()
    total_recursos = RecursoLeccion.objects.filter(leccion__curso__in=cursos_qs).count()
    total_inscripciones = Inscripcion.objects.filter(curso__in=cursos_qs).count() if es_admin else None
 
    context = {
        'titulo_pagina': 'Dashboard',
        'total_cursos': total_cursos,
        'cursos_publicados': cursos_publicados,
        'total_lecciones': total_lecciones,
        'total_recursos': total_recursos,
        'total_inscripciones': total_inscripciones,
    }
    return render(request, 'panel/dashboard.html', context)


# ---------------------------------------------------------------------------
# Cursos
# ---------------------------------------------------------------------------

class CursoListView(InstructorOrStaffMixin, ListView):
    """
    - Staff: ve todos los cursos.
    - Instructor: ve solo los cursos donde está asignado como instructor.
    """
    model = Curso
    template_name = 'panel/curso_list.html'
    context_object_name = 'cursos'
    ordering = ['-creado_en']

    def test_func(self):
        user = self.request.user
        es_admin = user.is_staff or user.groups.filter(name='Directivo / Coordinador').exists()
        return es_admin or user.groups.filter(name='Instructores').exists()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
 
        es_admin = user.is_staff or user.groups.filter(name='Directivo / Coordinador').exists()
 
        if es_admin:
            return queryset
 
        return queryset.filter(instructor=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        return context


class CursoCreateView(AdminOrStaffRequiredMixin, CreateView):
    """Solo staff puede crear cursos."""
    model = Curso
    form_class = CursoForm
    template_name = 'panel/curso_form.html'
    success_url = reverse_lazy('panel:curso_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = CursoLeccionFormSet(self.request.POST, self.request.FILES)
        else:
            context['formset'] = CursoLeccionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            if formset.is_valid():
                formset.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, 'Curso creado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        messages.error(self.request, 'Hubo errores en el formulario. Por favor, corrígelos.')
        return self.render_to_response(context)


class CursoUpdateView(AdminOrStaffRequiredMixin, UpdateView):
    """Solo staff puede editar cursos."""
    model = Curso
    form_class = CursoForm
    template_name = 'panel/curso_form.html'
    success_url = reverse_lazy('panel:curso_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = CursoLeccionFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context['formset'] = CursoLeccionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            if formset.is_valid():
                formset.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, 'Curso actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        messages.error(self.request, 'Hubo errores en el formulario. Por favor, corrígelos.')
        return self.render_to_response(context)


class CursoDeleteView(AdminOrStaffRequiredMixin, DeleteView):
    """Solo staff puede eliminar cursos."""
    model = Curso
    template_name = 'panel/curso_confirm_delete.html'
    success_url = reverse_lazy('panel:curso_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Curso eliminado correctamente.')
        return super().delete(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Lecciones
# ---------------------------------------------------------------------------

class LeccionListView(InstructorOrStaffMixin, ListView):
    """
    Lista todas las lecciones de un curso.
    - Staff: acceso libre.
    - Instructor: solo si es el instructor del curso.
    """
    model = Leccion
    template_name = 'panel/leccion_list.html'
    context_object_name = 'lecciones'

    def get_queryset(self):
        self.curso = get_object_or_404(Curso, pk=self.kwargs['curso_pk'])
        user = self.request.user
        
        es_admin = user.is_staff or user.groups.filter(name='Administradores').exists()
        
        # Verificar pertenencia al curso si no es admin o staff
        if not es_admin and self.curso.instructor != user:
            raise PermissionDenied("No tienes permiso para ver las lecciones de este curso.")

        return Leccion.objects.filter(curso=self.curso).order_by('orden')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['curso'] = self.curso
        context['titulo_pagina'] = f'Lecciones de {self.curso.titulo}'
        return context


class LeccionCreateView(CursoPermissionMixin, CreateView):
    """
    Crear una nueva lección para un curso.
    Permitido para staff o el instructor asignado al curso.
    """
    model = Leccion
    form_class = LeccionForm
    template_name = 'panel/leccion_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.curso = get_object_or_404(Curso, pk=self.kwargs['curso_pk'])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return (
            self.request.user.is_staff or
            self.request.user == self.curso.instructor
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Nueva lección para {self.curso.titulo}'
        context['curso'] = self.curso

        if 'recurso_formset' not in kwargs:
            if self.request.POST:
                context['recurso_formset'] = RecursoFormSet(
                    self.request.POST, self.request.FILES
                )
            else:
                context['recurso_formset'] = RecursoFormSet()
        else:
            context['recurso_formset'] = kwargs['recurso_formset']

        return context

    def form_valid(self, form):
        recurso_formset = RecursoFormSet(self.request.POST, self.request.FILES)

        # DEBUG TEMPORAL — borra esto después
        print("=== FORM ERRORS ===", form.errors)
        print("=== FORMSET ERRORS ===", recurso_formset.errors)
        print("=== FORMSET NON FORM ERRORS ===", recurso_formset.non_form_errors())
        print("=== POST DATA ===", self.request.POST)
        # FIN DEBUG

        form.instance.curso = self.curso

        if recurso_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                recurso_formset.instance = self.object
                recurso_formset.save()
            messages.success(self.request, 'Lección creada correctamente.')
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(
                self.get_context_data(form=form, recurso_formset=recurso_formset)
            )

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('panel:leccion_list', kwargs={'curso_pk': self.curso.pk})


class LeccionUpdateView(CursoPermissionMixin, UpdateView):
    """
    Editar una lección existente y sus recursos.
    Permitido para staff o el instructor asignado al curso.
    """
    model = Leccion
    form_class = LeccionForm
    template_name = 'panel/leccion_form.html'

    def test_func(self):
        leccion = get_object_or_404(Leccion, pk=self.kwargs['pk'])
        curso = leccion.curso
        return (
            self.request.user.is_staff or
            self.request.user == curso.instructor
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar lección: {self.object.titulo}'
        context['curso'] = self.object.curso

        if 'recurso_formset' not in kwargs:
            if self.request.POST:
                context['recurso_formset'] = RecursoFormSet(
                    self.request.POST, self.request.FILES, instance=self.object
                )
            else:
                context['recurso_formset'] = RecursoFormSet(instance=self.object)
        else:
            context['recurso_formset'] = kwargs['recurso_formset']

        return context

    def form_valid(self, form):
        recurso_formset = RecursoFormSet(
            self.request.POST, self.request.FILES, instance=self.object
        )

        # DEBUG TEMPORAL — borra esto después
        print("=== FORM ERRORS ===", form.errors)
        print("=== FORMSET ERRORS ===", recurso_formset.errors)
        print("=== FORMSET NON FORM ERRORS ===", recurso_formset.non_form_errors())
        print("=== POST DATA ===", self.request.POST)
        # FIN DEBUG

        if recurso_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                recurso_formset.instance = self.object
                recurso_formset.save()
            messages.success(self.request, 'Lección actualizada correctamente.')
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(
                self.get_context_data(form=form, recurso_formset=recurso_formset)
            )

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('panel:leccion_list', kwargs={'curso_pk': self.object.curso.pk})


class LeccionDeleteView(CursoPermissionMixin, DeleteView):
    """Solo staff o el instructor del curso puede eliminar lecciones."""
    model = Leccion
    template_name = 'panel/leccion_confirm_delete.html'

    def test_func(self):
        leccion = get_object_or_404(Leccion, pk=self.kwargs['pk'])
        curso = leccion.curso
        return (
            self.request.user.is_staff or
            self.request.user == curso.instructor
        )

    def get_success_url(self):
        return reverse('panel:leccion_list', kwargs={'curso_pk': self.object.curso.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Eliminar lección'
        context['curso'] = self.object.curso
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Lección eliminada correctamente.')
        return super().delete(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Inscripciones  (solo staff)
# ---------------------------------------------------------------------------

class InscripcionListView(InstructorCanViewInscripcionesMixin, ListView):
    """Listado de inscripciones con filtros. 
    Admins ven todas; Instructores ven solo las de sus cursos."""
    model = Inscripcion
    template_name = 'panel/inscripcion_list.html'
    context_object_name = 'inscripciones'
    paginate_by = 20

    def get_queryset(self):
        # 1. Obtenemos todas las inscripciones inicialmente
        queryset = Inscripcion.objects.select_related('estudiante', 'curso').order_by('-inscrito_en')

        # 2. Validamos el rol del usuario actual
        user = self.request.user
        es_admin = user.is_staff or user.groups.filter(name='Directivo / Coordinador').exists()

        # 3. FILTRO DE SEGURIDAD: Si es instructor, limitamos a sus propios cursos
        if not es_admin:
            queryset = queryset.filter(curso__instructor=user)

        # 4. Aplicamos los filtros de búsqueda que ya tenías (GET params)
        curso_id = self.request.GET.get('curso')
        usuario_id = self.request.GET.get('usuario')
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if curso_id:
            queryset = queryset.filter(curso_id=curso_id)
        if usuario_id:
            queryset = queryset.filter(estudiante_id=usuario_id)
        if estado == 'completado':
            queryset = queryset.filter(completado=True)
        elif estado == 'en_progreso':
            queryset = queryset.filter(completado=False)
        if busqueda:
            queryset = queryset.filter(
                Q(estudiante__username__icontains=busqueda) |
                Q(estudiante__email__icontains=busqueda) |
                Q(estudiante__full_name__icontains=busqueda) |
                Q(curso__titulo__icontains=busqueda)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Inscripciones'
        
        user = self.request.user
        es_admin = user.is_staff or user.groups.filter(name='Directivo / Coordinador').exists()

        # El selector de "Cursos" en el HTML solo debe mostrar los cursos permitidos
        if es_admin:
            cursos_qs = Curso.objects.filter(publicado=True).order_by('titulo')
        else:
            cursos_qs = Curso.objects.filter(instructor=user, publicado=True).order_by('titulo')

        context['cursos'] = cursos_qs
        context['usuarios'] = CustomUser.objects.filter(is_active=True).order_by('username')
        context['curso_seleccionado'] = self.request.GET.get('curso', '')
        context['usuario_seleccionado'] = self.request.GET.get('usuario', '')
        context['estado_seleccionado'] = self.request.GET.get('estado', '')
        context['busqueda'] = self.request.GET.get('busqueda', '')
        return context


class EstudianteSearchView(LoginRequiredMixin, View):
    """
    GET /panel/estudiantes/buscar/?q=ana
    Devuelve hasta 20 estudiantes que coincidan por nombre, username o email.
    """
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()

        if len(q) < 2:
            return JsonResponse({'results': []})

        estudiantes = CustomUser.objects.filter(
            Q(full_name__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q)
        ).order_by('full_name')[:20]

        results = [
            {
                'id': u.id,
                'username': u.username,
                'full_name': u.full_name,
                'email': u.email,
            }
            for u in estudiantes
        ]
        return JsonResponse({'results': results})


class EstudianteRapidoCreateView(LoginRequiredMixin, View):
    """
    POST /panel/estudiantes/crear-rapido/
    Crea una cuenta mínima de estudiante con username y password generados automáticamente.
    """
    def post(self, request, *args, **kwargs):
        form = EstudianteRapidoForm(request.POST)

        if not form.is_valid():
            return JsonResponse(
                {'success': False, 'errors': _form_errors_dict(form)},
                status=422,
            )

        full_name = form.cleaned_data['full_name']
        email = form.cleaned_data['email']

        username = generar_username(full_name, email)
        password = generar_password_temporal()

        estudiante = form.save(commit=False)
        estudiante.username = username
        estudiante.set_password(password)
        estudiante.save()

        messages.success(
            request,
            f'Cuenta creada para {estudiante.full_name} (usuario: {username})'
        )

        return JsonResponse({
            'success': True,
            'estudiante': {
                'id': estudiante.id,
                'username': estudiante.username,
                'full_name': estudiante.full_name,
                'email': estudiante.email,
            },
            'credenciales': {
                'username': username,
                'password': password,
            },
        })


class InscripcionCreateView(AdminOrStaffRequiredMixin, CreateView):
    """Solo staff puede inscribir usuarios."""
    model = Inscripcion
    form_class = InscripcionForm
    template_name = 'panel/inscripcion_form.html'
    success_url = reverse_lazy('panel:inscripcion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Nueva inscripción'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Usuario {form.instance.estudiante.username} inscrito correctamente en {form.instance.curso.titulo}'
        )
        if _is_ajax(self.request):
            return JsonResponse({'success': True})
        return response

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse(
                {'success': False, 'errors': _form_errors_dict(form)},
                status=422,
            )
        return super().form_invalid(form)


class InscripcionUpdateView(AdminOrStaffRequiredMixin, UpdateView):
    """Solo staff puede editar inscripciones."""
    model = Inscripcion
    form_class = InscripcionForm
    template_name = 'panel/inscripcion_form.html'
    success_url = reverse_lazy('panel:inscripcion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar inscripción: {self.object.estudiante.username} - {self.object.curso.titulo}'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Inscripción actualizada correctamente')
        if _is_ajax(self.request):
            return JsonResponse({'success': True})
        return response

    def form_invalid(self, form):
        if _is_ajax(self.request):
            return JsonResponse(
                {'success': False, 'errors': _form_errors_dict(form)},
                status=422,
            )
        return super().form_invalid(form)


class InscripcionDeleteView(AdminOrStaffRequiredMixin, DeleteView):
    """Solo staff puede eliminar inscripciones."""
    model = Inscripcion
    template_name = 'panel/inscripcion_confirm_delete.html'
    success_url = reverse_lazy('panel:inscripcion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Eliminar inscripción'
        return context

    def delete(self, request, *args, **kwargs):
        inscripcion = self.get_object()
        messages.success(
            request,
            f'Inscripción de {inscripcion.estudiante.username} en {inscripcion.curso.titulo} eliminada correctamente'
        )
        return super().delete(request, *args, **kwargs)


class InscripcionDetailView(AdminOrStaffRequiredMixin, DetailView):
    """Solo staff puede ver detalles de inscripciones."""
    model = Inscripcion
    template_name = 'panel/inscripcion_detail.html'
    context_object_name = 'inscripcion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Detalles de inscripción: {self.object.estudiante.username}'
        from courses.models import LeccionCompletada
        lecciones_completadas = LeccionCompletada.objects.filter(
            inscripcion=self.object
        ).select_related('leccion')
        context['lecciones_completadas'] = lecciones_completadas
        context['total_lecciones'] = self.object.curso.lecciones.count()
        return context


# ---------------------------------------------------------------------------
# Usuarios  (AdminOrStaffRequiredMixin — staff o grupo "Administradores")
# ---------------------------------------------------------------------------

class UsuarioListView(AdminOrStaffRequiredMixin, ListView):
    """Staff o administradores pueden ver el listado de usuarios."""
    model = CustomUser
    template_name = 'panel/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by('-date_joined')
 
        busqueda = self.request.GET.get('busqueda', '')
        rol = self.request.GET.get('rol', '')
        activo = self.request.GET.get('activo', '')
 
        if busqueda:
            queryset = queryset.filter(
                Q(username__icontains=busqueda) |
                Q(email__icontains=busqueda) |
                Q(full_name__icontains=busqueda)
            )
 
        if rol == 'sistema':
            queryset = queryset.filter(is_staff=True)
        elif rol == 'directivo':
            queryset = queryset.filter(groups__name='Directivo / Coordinador')
        elif rol == 'instructor':
            queryset = queryset.filter(groups__name='Instructores')
        elif rol == 'estudiante':
            queryset = queryset.filter(is_staff=False).exclude(
                groups__name__in=['Directivo / Coordinador', 'Instructores']
            )
 
        if activo == 'si':
            queryset = queryset.filter(is_active=True)
        elif activo == 'no':
            queryset = queryset.filter(is_active=False)
 
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Usuarios'
        context['form_filtro'] = UsuarioFiltroForm(self.request.GET)
        context['total_usuarios'] = CustomUser.objects.count()
        context['total_activos'] = CustomUser.objects.filter(is_active=True).count()
        context['total_staff'] = CustomUser.objects.filter(is_staff=True).count()
        return context


class UsuarioCreateView(AdminOrStaffRequiredMixin, CreateView):
    """Staff o administradores pueden crear usuarios."""
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'panel/usuario_form.html'

    def get(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return redirect('panel:usuario_list')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Crear usuario'
        return context

    def form_valid(self, form):
        if not form.cleaned_data.get('password'):
            password_temporal = generar_password_temporal()
            form.instance.set_password(password_temporal)
        else:
            password_temporal = form.cleaned_data.get('password')

        response = super().form_valid(form)

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'usuario': {
                    'id': self.object.pk,
                    'username': self.object.username,
                    'email': self.object.email,
                    'full_name': self.object.get_full_name(),
                },
                'credenciales': {
                    'username': self.object.username,
                    'password': password_temporal,
                }
            })

        messages.success(self.request, f'Usuario {self.object.username} creado correctamente.')
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=422)

        context = self.get_context_data(form=form)
        messages.error(self.request, 'Hubo errores en el formulario.')
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('panel:usuario_list')


class UsuarioUpdateView(AdminOrStaffRequiredMixin, UpdateView):
    """Staff o administradores pueden editar usuarios."""
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'panel/usuario_form.html'

    def get(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return redirect('panel:usuario_list')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar usuario: {self.object.username}'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'usuario': {
                    'id': self.object.pk,
                    'username': self.object.username,
                    'email': self.object.email,
                    'full_name': self.object.get_full_name(),
                }
            })

        messages.success(self.request, f'Usuario {self.object.username} actualizado correctamente.')
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=422)

        context = self.get_context_data(form=form)
        messages.error(self.request, 'Hubo errores en el formulario.')
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('panel:usuario_list')


class UsuarioDeleteView(AdminOrStaffRequiredMixin, DeleteView):
    """Staff o administradores pueden eliminar usuarios."""
    model = CustomUser
    template_name = 'panel/usuario_confirm_delete.html'
    success_url = reverse_lazy('panel:usuario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Eliminar usuario'
        context['tiene_inscripciones'] = self.object.inscripciones.exists()
        context['total_inscripciones'] = self.object.inscripciones.count()
        return context

    def delete(self, request, *args, **kwargs):
        usuario = self.get_object()
        username = usuario.username

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            usuario.delete()
            return JsonResponse({'success': True})

        messages.success(request, f'Usuario {username} eliminado correctamente.')
        return super().delete(request, *args, **kwargs)


class UsuarioDetailView(AdminOrStaffRequiredMixin, DetailView):
    """Staff o administradores pueden ver el detalle de un usuario."""
    model = CustomUser
    template_name = 'panel/usuario_detail.html'
    context_object_name = 'usuario'

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            usuario = self.get_object()
            inscripciones = Inscripcion.objects.filter(
                estudiante=usuario
            ).select_related('curso')
            return JsonResponse({
                'inscripciones': [
                    {
                        'curso': ins.curso.titulo,
                        'completado': ins.completado,
                    }
                    for ins in inscripciones
                ]
            })
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Detalles de {self.object.username}'
        from courses.models import Inscripcion, LeccionCompletada
        inscripciones = Inscripcion.objects.filter(estudiante=self.object).select_related('curso')
        context['inscripciones'] = inscripciones
        context['total_inscripciones'] = inscripciones.count()
        context['total_completados'] = inscripciones.filter(completado=True).count()
        context['lecciones_completadas'] = LeccionCompletada.objects.filter(
            inscripcion__estudiante=self.object
        ).count()
        return context


class UsuarioResetPasswordView(AdminOrStaffRequiredMixin, View):
    """Staff o administradores pueden restablecer contraseñas."""
    def post(self, request, *args, **kwargs):
        usuario = get_object_or_404(CustomUser, pk=kwargs['pk'])
        nueva_password = generar_password_temporal()
        usuario.set_password(nueva_password)
        usuario.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'username': usuario.username,
                'password': nueva_password,
            })

        messages.success(request, f'Contraseña restablecida para {usuario.username}')
        return redirect('panel:usuario_detail', pk=usuario.pk)


from django.views.generic import TemplateView
from django.db.models import Count
from django.db.models.functions import TruncMonth
from datetime import timedelta
from tests.models import ResultadoValores, ResultadoDomino
from django.utils import timezone
from xhtml2pdf import pisa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def _get_dashboard_analitico_data(desde_dt, hasta_dt):
    """Queries del Módulo 1, compartidas entre la vista HTML y la de PDF."""
    resultados_allport = ResultadoValores.objects.filter(fecha_completado__range=(desde_dt, hasta_dt))
    resultados_domino = ResultadoDomino.objects.filter(fecha__range=(desde_dt, hasta_dt))
    inscripciones_qs = Inscripcion.objects.filter(inscrito_en__range=(desde_dt, hasta_dt))

    total_pruebas = resultados_allport.count() + resultados_domino.count()
    total_cursos_publicados = Curso.objects.filter(publicado=True).count()
    total_inscripciones = inscripciones_qs.count()
    total_usuarios = CustomUser.objects.count()

    total_inscripciones_general = Inscripcion.objects.count()
    completadas_general = Inscripcion.objects.filter(completado=True).count()
    tasa_finalizacion = (
        round(completadas_general / total_inscripciones_general * 100, 1)
        if total_inscripciones_general else 0
    )

    pruebas_por_mes = (resultados_allport.annotate(mes=TruncMonth('fecha_completado'))
                        .values('mes').annotate(total=Count('id')).order_by('mes'))
    domino_por_mes = (resultados_domino.annotate(mes=TruncMonth('fecha'))
                       .values('mes').annotate(total=Count('id')).order_by('mes'))
    inscripciones_por_mes = (inscripciones_qs.annotate(mes=TruncMonth('inscrito_en'))
                              .values('mes').annotate(total=Count('id')).order_by('mes'))

    meses = sorted(set(
        [p['mes'] for p in pruebas_por_mes] +
        [d['mes'] for d in domino_por_mes] +
        [i['mes'] for i in inscripciones_por_mes]
    ))

    def _serie(datos):
        mapa = {d['mes']: d['total'] for d in datos}
        return [mapa.get(m, 0) for m in meses]

    allport_serie = _serie(pruebas_por_mes)
    domino_serie = _serie(domino_por_mes)
    evolucion_mensual = {
        'labels': [m.strftime('%b %Y') for m in meses],
        'pruebas': [a + d for a, d in zip(allport_serie, domino_serie)],
        'inscripciones': _serie(inscripciones_por_mes),
    }

    distribucion_pruebas = {
        'labels': ['Allport', 'Dominó'],
        'data': [resultados_allport.count(), resultados_domino.count()],
    }

    top_cursos = (Curso.objects.annotate(num_inscripciones=Count('inscripciones'))
                  .order_by('-num_inscripciones')[:5])
    top_cursos_data = {
        'labels': [c.titulo for c in top_cursos],
        'data': [c.num_inscripciones for c in top_cursos],
    }

    movimientos = []
    for i in inscripciones_qs.select_related('estudiante', 'curso').order_by('-inscrito_en')[:10]:
        movimientos.append({'tipo': 'inscripcion', 'descripcion': f'{i.estudiante.full_name} se inscribió a "{i.curso.titulo}"', 'fecha': i.inscrito_en})
    for r in resultados_allport.select_related('usuario').order_by('-fecha_completado')[:10]:
        movimientos.append({'tipo': 'prueba_allport', 'descripcion': f'{r.usuario.full_name} completó el Test de Valores (Allport)', 'fecha': r.fecha_completado})
    for r in resultados_domino.select_related('usuario').order_by('-fecha')[:10]:
        movimientos.append({'tipo': 'prueba_domino', 'descripcion': f'{r.usuario.full_name} completó el Test de Dominó D-48', 'fecha': r.fecha})
    movimientos.sort(key=lambda m: m['fecha'], reverse=True)

    return {
        'total_pruebas': total_pruebas,
        'total_cursos_publicados': total_cursos_publicados,
        'total_inscripciones': total_inscripciones,
        'total_usuarios': total_usuarios,
        'tasa_finalizacion': tasa_finalizacion,
        'evolucion_mensual': evolucion_mensual,
        'distribucion_pruebas': distribucion_pruebas,
        'top_cursos_data': top_cursos_data,
        'movimientos': movimientos[:10],
    }

def _get_logo_base64():
    """Lee el logo institucional y lo devuelve en base64 para embeber en el PDF."""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_completo.jpg')
    try:
        with open(logo_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        return None

class ReporteDashboardView(AdminOrStaffRequiredMixin, TemplateView):
    """
    Módulo 1: Dashboard analítico general.
    Acceso restringido a Administrador del Sistema / Directivo (AdminOrStaffRequiredMixin).
    """
    template_name = 'panel/reportes/dashboard_analitico.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- Filtros: rango de fechas (desde/hasta por GET) ---
        desde = self.request.GET.get('desde')
        hasta = self.request.GET.get('hasta')
        hoy = timezone.now()

        if hasta:
            hasta_dt = timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        else:
            hasta_dt = hoy

        if desde:
            desde_dt = timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d'))
        else:
            desde_dt = hoy - timedelta(days=365)  # ventana amplia por defecto

        # --- Querysets base filtrados por rango ---
        context.update(_get_dashboard_analitico_data(desde_dt, hasta_dt))
        context.update({
            'titulo_pagina': 'Dashboard analítico',
            'desde': desde_dt.date(),
            'hasta': hasta_dt.date(),
        })
        return context

@login_required
def generar_pdf_dashboard(request):
    user = request.user
    if not (user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()):
        raise PermissionDenied("Se requieren permisos de administrador para esta acción.")

    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    hoy = timezone.now()
    hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)) if hasta else hoy)
    desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d')) if desde else hoy - timedelta(days=365))

    datos = _get_dashboard_analitico_data(desde_dt, hasta_dt)
    dorado, salvia, arena = '#a08848', '#709888', '#d8c898'

    # --- Línea: evolución mensual ---
    ev = datos['evolucion_mensual']
    plt.figure(figsize=(8, 4), facecolor='white')
    plt.plot(ev['labels'], ev['pruebas'], color=dorado, marker='o', label='Pruebas')
    plt.plot(ev['labels'], ev['inscripciones'], color=salvia, marker='o', label='Inscripciones')
    plt.xticks(rotation=45, ha='right', fontsize=8)
    plt.legend()
    plt.title('Evolución mensual', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    grafico_evolucion = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    # --- Pastel: distribución de pruebas ---
    dp = datos['distribucion_pruebas']
    plt.figure(figsize=(4, 4), facecolor='white')
    plt.pie(dp['data'], labels=dp['labels'], autopct='%1.0f%%', colors=[dorado, salvia])
    plt.title('Pruebas por tipo', fontsize=12, fontweight='bold')
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    grafico_distribucion = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    # --- Barras: top 5 cursos ---
    tc = datos['top_cursos_data']
    plt.figure(figsize=(7, 3.5), facecolor='white')
    plt.barh(tc['labels'][::-1], tc['data'][::-1], color=arena)
    plt.title('Top 5 cursos con más inscripciones', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    grafico_top_cursos = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()

    context = {
        **datos,
        'grafico_evolucion': grafico_evolucion,
        'grafico_distribucion': grafico_distribucion,
        'grafico_top_cursos': grafico_top_cursos,
        'logo_base64': _get_logo_base64(),
        'desde': desde_dt.date(),
        'hasta': hasta_dt.date(),
        'fecha_generacion': timezone.now(),
    }

    template = get_template('panel/reportes/pdf/dashboard_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_dashboard_centro_dhae.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response


from django.db.models import Avg
from django.core.paginator import Paginator

def _get_pruebas_resumen_data(desde_dt, hasta_dt, tipo_prueba='ambas', genero=None, institucion=None, grupo_edad=None):
    """Resumen y distribuciones del Módulo 2, compartido entre la vista HTML y el PDF."""
    resultados_allport = ResultadoValores.objects.select_related('usuario', 'test').filter(
        fecha_completado__range=(desde_dt, hasta_dt)
    )
    resultados_domino = ResultadoDomino.objects.select_related('usuario', 'test').filter(
        fecha__range=(desde_dt, hasta_dt)
    )

    if genero:
        resultados_allport = resultados_allport.filter(usuario__gender=genero)
        resultados_domino = resultados_domino.filter(usuario__gender=genero)
    if institucion:
        resultados_allport = resultados_allport.filter(usuario__institution=institucion)
        resultados_domino = resultados_domino.filter(usuario__institution=institucion)
    if grupo_edad:
        resultados_domino = resultados_domino.filter(grupo_edad=grupo_edad)

    if tipo_prueba == 'allport':
        resultados_domino = ResultadoDomino.objects.none()
    elif tipo_prueba == 'domino':
        resultados_allport = ResultadoValores.objects.none()

    total_allport = resultados_allport.count()
    total_domino = resultados_domino.count()

    promedios_allport = resultados_allport.aggregate(
        teorico=Avg('teorico'), economico=Avg('economico'), estetico=Avg('estetico'),
        social=Avg('social'), politico=Avg('politico'), religioso=Avg('religioso'),
    )
    promedio_percentil_domino = resultados_domino.aggregate(percentil=Avg('percentil'))['percentil']

    GENERO_LABELS = dict(CustomUser.GENDER_CHOICES)
    genero_counts = {}
    for row in resultados_allport.values('usuario__gender').annotate(total=Count('id')):
        genero_counts[row['usuario__gender']] = genero_counts.get(row['usuario__gender'], 0) + row['total']
    for row in resultados_domino.values('usuario__gender').annotate(total=Count('id')):
        genero_counts[row['usuario__gender']] = genero_counts.get(row['usuario__gender'], 0) + row['total']
    distribucion_genero = {
        'labels': [GENERO_LABELS.get(g, 'Sin especificar') for g in genero_counts],
        'data': list(genero_counts.values()),
    }

    edad_qs = resultados_domino.values('grupo_edad').annotate(total=Count('id')).order_by('-total')
    distribucion_edad = {
        'labels': [e['grupo_edad'] or 'Sin especificar' for e in edad_qs],
        'data': [e['total'] for e in edad_qs],
    }

    inst_counts = {}
    for row in (resultados_allport.exclude(usuario__institution__isnull=True).exclude(usuario__institution='')
                .values('usuario__institution').annotate(total=Count('id'))):
        inst_counts[row['usuario__institution']] = inst_counts.get(row['usuario__institution'], 0) + row['total']
    for row in (resultados_domino.exclude(usuario__institution__isnull=True).exclude(usuario__institution='')
                .values('usuario__institution').annotate(total=Count('id'))):
        inst_counts[row['usuario__institution']] = inst_counts.get(row['usuario__institution'], 0) + row['total']
    top_instituciones = sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    distribucion_institucion = {
        'labels': [i[0] for i in top_instituciones],
        'data': [i[1] for i in top_instituciones],
    }

    return {
        'resultados_allport': resultados_allport,
        'resultados_domino': resultados_domino,
        'total_allport': total_allport,
        'total_domino': total_domino,
        'total_general': total_allport + total_domino,
        'promedios_allport': promedios_allport,
        'promedio_percentil_domino': promedio_percentil_domino,
        'distribucion_genero': distribucion_genero,
        'distribucion_edad': distribucion_edad,
        'distribucion_institucion': distribucion_institucion,
    }


class ReportePruebasView(AdminOrStaffRequiredMixin, TemplateView):
    """
    Módulo 2: Reportes de pruebas psicológicas (Allport + Dominó).
    """
    template_name = 'panel/reportes/reporte_pruebas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # --- Filtros ---
        tipo_prueba = request.GET.get('tipo_prueba', 'ambas')  # 'allport' | 'domino' | 'ambas'
        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        genero = request.GET.get('genero')
        institucion = request.GET.get('institucion')
        grupo_edad = request.GET.get('grupo_edad')
        page_num = request.GET.get('page', 1)

        hoy = timezone.now()
        hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
                    if hasta else hoy)
        desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d'))
                    if desde else hoy - timedelta(days=365))

        datos = _get_pruebas_resumen_data(desde_dt, hasta_dt, tipo_prueba, genero, institucion, grupo_edad)
        resultados_allport = datos['resultados_allport']
        resultados_domino = datos['resultados_domino']

        # --- Tabla detallada (combinada y paginada) ---
        filas = []
        import unicodedata

        def _normalizar(txt):
            """Quita acentos y pasa a minúsculas, para comparar 'Político' con 'politico'."""
            txt = unicodedata.normalize('NFKD', txt or '')
            return txt.encode('ascii', 'ignore').decode('ascii').lower().strip()

        VALORES_ALLPORT = ['teorico', 'economico', 'estetico', 'social', 'politico', 'religioso']

        for r in resultados_allport:
            clave = _normalizar(r.valor_dominante)
            puntaje = getattr(r, clave, None) if clave in VALORES_ALLPORT else None
            if puntaje is not None:
                texto_puntaje = f'{r.valor_dominante}: {puntaje:.0f} pts'
            else:
                texto_puntaje = r.valor_dominante or '—'

            filas.append({
                'usuario': r.usuario.full_name,
                'prueba': 'Allport',
                'fecha': r.fecha_completado,
                'puntaje_percentil': texto_puntaje,
                'diagnostico': r.valor_dominante or '—',
            })
        for r in resultados_domino:
            filas.append({
                'usuario': r.usuario.full_name,
                'prueba': 'Dominó D-48',
                'fecha': r.fecha,
                'puntaje_percentil': f'{r.puntuacion} pts / P{r.percentil}' if r.percentil else f'{r.puntuacion} pts',
                'diagnostico': r.diagnostico or '—',
            })
        filas.sort(key=lambda f: f['fecha'], reverse=True)

        paginator = Paginator(filas, 20)
        page_obj = paginator.get_page(page_num)

        context.update({
            **datos,
            'titulo_pagina': 'Reporte de pruebas',
            'tipo_prueba': tipo_prueba,
            'desde': desde_dt.date(),
            'hasta': hasta_dt.date(),
            'genero': genero,
            'institucion': institucion,
            'grupo_edad': grupo_edad,
            'generos_choices': CustomUser.GENDER_CHOICES,
            'instituciones_choices': (CustomUser.objects.exclude(institution__isnull=True).exclude(institution='')
                                       .values_list('institution', flat=True).distinct().order_by('institution')),
            'grupos_edad_choices': ResultadoDomino.objects.exclude(grupo_edad='').values_list('grupo_edad', flat=True).distinct(),
            'page_obj': page_obj,
        })
        return context

@login_required
def generar_pdf_pruebas(request):
    user = request.user
    if not (user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()):
        raise PermissionDenied("Se requieren permisos de administrador para esta acción.")

    tipo_prueba = request.GET.get('tipo_prueba', 'ambas')
    genero = request.GET.get('genero') or None
    institucion = request.GET.get('institucion') or None
    grupo_edad = request.GET.get('grupo_edad') or None
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')

    hoy = timezone.now()
    hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)) if hasta else hoy)
    desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d')) if desde else hoy - timedelta(days=365))

    datos = _get_pruebas_resumen_data(desde_dt, hasta_dt, tipo_prueba, genero, institucion, grupo_edad)
    dorado, salvia, arena, calido = '#a08848', '#709888', '#d8c898', '#c09060'

    dg = datos['distribucion_genero']
    plt.figure(figsize=(4, 4), facecolor='white')
    plt.pie(dg['data'], labels=dg['labels'], autopct='%1.0f%%', colors=[dorado, salvia, arena, calido])
    plt.title('Distribución por género', fontsize=12, fontweight='bold')
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_genero = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    de = datos['distribucion_edad']
    plt.figure(figsize=(6, 3.5), facecolor='white')
    plt.bar(de['labels'], de['data'], color=salvia)
    plt.title('Distribución por grupo de edad (Dominó)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_edad = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    pa = datos['promedios_allport']
    labels_allport = ['Teórico', 'Económico', 'Estético', 'Social', 'Político', 'Religioso']
    valores_allport = [pa['teorico'] or 0, pa['economico'] or 0, pa['estetico'] or 0, pa['social'] or 0, pa['politico'] or 0, pa['religioso'] or 0]
    plt.figure(figsize=(6, 3.5), facecolor='white')
    plt.bar(labels_allport, valores_allport, color=dorado)
    plt.title('Promedios Allport', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_allport = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    di = datos['distribucion_institucion']
    plt.figure(figsize=(7, 3.5), facecolor='white')
    plt.barh(di['labels'][::-1], di['data'][::-1], color=arena)
    plt.title('Top 10 instituciones', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_institucion = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    context = {
        **datos,
        'grafico_genero': grafico_genero,
        'grafico_edad': grafico_edad,
        'grafico_allport': grafico_allport,
        'grafico_institucion': grafico_institucion,
        'logo_base64': _get_logo_base64(),
        'desde': desde_dt.date(),
        'hasta': hasta_dt.date(),
        'fecha_generacion': timezone.now(),
    }

    template = get_template('panel/reportes/pdf/pruebas_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_pruebas_centro_dhae.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response

def _get_cursos_resumen_data(desde_dt, hasta_dt, curso_id=None, instructor_id=None, estado='todos'):
    """Resumen y distribuciones del Módulo 3, compartido entre la vista HTML y el PDF."""
    cursos_qs = Curso.objects.select_related('instructor')
    if curso_id:
        cursos_qs = cursos_qs.filter(pk=curso_id)
    if instructor_id:
        cursos_qs = cursos_qs.filter(instructor_id=instructor_id)
    if estado == 'publicado':
        cursos_qs = cursos_qs.filter(publicado=True)
    elif estado == 'no_publicado':
        cursos_qs = cursos_qs.filter(publicado=False)

    inscripciones_qs = Inscripcion.objects.filter(
        curso__in=cursos_qs, inscrito_en__range=(desde_dt, hasta_dt)
    )

    total_cursos = cursos_qs.count()
    total_inscripciones = inscripciones_qs.count()
    completadas = inscripciones_qs.filter(completado=True).count()
    tasa_finalizacion_global = round(completadas / total_inscripciones * 100, 1) if total_inscripciones else 0
    progreso_promedio_global = inscripciones_qs.aggregate(avg=Avg('progreso'))['avg'] or 0

    cursos_detalle = cursos_qs.annotate(
        num_inscripciones=Count('inscripciones', filter=Q(inscripciones__inscrito_en__range=(desde_dt, hasta_dt))),
        num_completados=Count('inscripciones', filter=Q(inscripciones__completado=True, inscripciones__inscrito_en__range=(desde_dt, hasta_dt))),
        progreso_promedio=Avg('inscripciones__progreso', filter=Q(inscripciones__inscrito_en__range=(desde_dt, hasta_dt))),
    ).order_by('-num_inscripciones')

    tabla_cursos = []
    for c in cursos_detalle:
        tasa = round(c.num_completados / c.num_inscripciones * 100, 1) if c.num_inscripciones else 0
        tabla_cursos.append({
            'curso': c,
            'instructor': c.instructor.full_name if c.instructor else 'Sin asignar',
            'inscripciones': c.num_inscripciones,
            'completados': c.num_completados,
            'tasa_finalizacion': tasa,
            'progreso_promedio': round(c.progreso_promedio, 1) if c.progreso_promedio else 0,
        })

    top10 = tabla_cursos[:10]
    top_cursos_inscripciones = {
        'labels': [t['curso'].titulo for t in top10],
        'data': [t['inscripciones'] for t in top10],
    }

    distribucion_estado = {
        'labels': ['Completadas', 'En progreso'],
        'data': [completadas, total_inscripciones - completadas],
    }

    insc_por_mes = (inscripciones_qs.annotate(mes=TruncMonth('inscrito_en'))
                     .values('mes').annotate(total=Count('id')).order_by('mes'))
    evolucion_inscripciones = {
        'labels': [i['mes'].strftime('%b %Y') for i in insc_por_mes],
        'data': [i['total'] for i in insc_por_mes],
    }

    return {
        'total_cursos': total_cursos,
        'total_inscripciones': total_inscripciones,
        'tasa_finalizacion_global': tasa_finalizacion_global,
        'progreso_promedio_global': round(progreso_promedio_global, 1),
        'tabla_cursos': tabla_cursos,
        'top_cursos_inscripciones': top_cursos_inscripciones,
        'distribucion_estado': distribucion_estado,
        'evolucion_inscripciones': evolucion_inscripciones,
    }

class ReporteCursosView(AdminOrStaffRequiredMixin, TemplateView):
    """
    Módulo 3: Reportes de cursos y formación.
    """
    template_name = 'panel/reportes/reporte_cursos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # --- Filtros ---
        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        curso_id = request.GET.get('curso')
        instructor_id = request.GET.get('instructor')
        estado = request.GET.get('estado', 'todos')  # 'publicado' | 'no_publicado' | 'todos'

        hoy = timezone.now()
        hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
                    if hasta else hoy)
        desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d'))
                    if desde else hoy - timedelta(days=365))

        datos = _get_cursos_resumen_data(desde_dt, hasta_dt, curso_id, instructor_id, estado)

        context.update({
            **datos,
            'titulo_pagina': 'Reporte de cursos',
            'desde': desde_dt.date(),
            'hasta': hasta_dt.date(),
            'curso_id': int(curso_id) if curso_id else None,
            'instructor_id': int(instructor_id) if instructor_id else None,
            'estado': estado,
            'cursos_choices': Curso.objects.values('id', 'titulo').order_by('titulo'),
            'instructores_choices': (CustomUser.objects.filter(cursos_impartidos__isnull=False)
                                      .distinct().order_by('full_name')),
        })
        return context

@login_required
def generar_pdf_cursos(request):
    user = request.user
    if not (user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()):
        raise PermissionDenied("Se requieren permisos de administrador para esta acción.")

    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    curso_id = request.GET.get('curso') or None
    instructor_id = request.GET.get('instructor') or None
    estado = request.GET.get('estado', 'todos')

    hoy = timezone.now()
    hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)) if hasta else hoy)
    desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d')) if desde else hoy - timedelta(days=365))

    datos = _get_cursos_resumen_data(desde_dt, hasta_dt, curso_id, instructor_id, estado)
    dorado, salvia, arena = '#a08848', '#709888', '#d8c898'

    tc = datos['top_cursos_inscripciones']
    plt.figure(figsize=(7, 3.5), facecolor='white')
    plt.barh(tc['labels'][::-1], tc['data'][::-1], color=dorado)
    plt.title('Top 10 cursos por inscripciones', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_top_cursos = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    de = datos['distribucion_estado']
    plt.figure(figsize=(4, 4), facecolor='white')
    plt.pie(de['data'], labels=de['labels'], autopct='%1.0f%%', colors=[salvia, arena])
    plt.title('Estado de inscripciones', fontsize=12, fontweight='bold')
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_estado = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    ev = datos['evolucion_inscripciones']
    plt.figure(figsize=(8, 4), facecolor='white')
    plt.plot(ev['labels'], ev['data'], color=dorado, marker='o')
    plt.xticks(rotation=45, ha='right', fontsize=8)
    plt.title('Evolución mensual de inscripciones', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_evolucion = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    context = {
        **datos,
        'grafico_top_cursos': grafico_top_cursos,
        'grafico_estado': grafico_estado,
        'grafico_evolucion': grafico_evolucion,
        'logo_base64': _get_logo_base64(),
        'desde': desde_dt.date(),
        'hasta': hasta_dt.date(),
        'fecha_generacion': timezone.now(),
    }

    template = get_template('panel/reportes/pdf/cursos_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_cursos_centro_dhae.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response

from panel.mixins import GRUPO_DIRECTIVO, GRUPO_INSTRUCTORES

def _get_usuarios_resumen_data():
    """Resumen global del Módulo 4 — no depende de los filtros de búsqueda de la tabla."""
    total_usuarios = CustomUser.objects.count()
    activos = CustomUser.objects.filter(is_active=True).count()
    inactivos = total_usuarios - activos

    todos_directivos = CustomUser.objects.filter(is_staff=False, groups__name=GRUPO_DIRECTIVO).distinct().count()
    todos_instructores = CustomUser.objects.filter(is_staff=False, groups__name=GRUPO_INSTRUCTORES).exclude(groups__name=GRUPO_DIRECTIVO).distinct().count()
    todos_sistema = CustomUser.objects.filter(is_staff=True).count()
    todos_estudiantes = total_usuarios - todos_directivos - todos_instructores - todos_sistema

    distribucion_rol = {
        'labels': ['Administrador del Sistema', 'Directivo / Coordinador', 'Instructores', 'Estudiantes'],
        'data': [todos_sistema, todos_directivos, todos_instructores, todos_estudiantes],
    }
    activos_inactivos = {'labels': ['Activos', 'Inactivos'], 'data': [activos, inactivos]}

    nuevos_por_mes = (CustomUser.objects.annotate(mes=TruncMonth('date_joined'))
                       .values('mes').annotate(total=Count('id')).order_by('mes'))
    nuevos_usuarios_mes = {
        'labels': [n['mes'].strftime('%b %Y') for n in nuevos_por_mes if n['mes']],
        'data': [n['total'] for n in nuevos_por_mes if n['mes']],
    }

    return {
        'total_usuarios': total_usuarios,
        'activos': activos,
        'inactivos': inactivos,
        'distribucion_rol': distribucion_rol,
        'activos_inactivos': activos_inactivos,
        'nuevos_usuarios_mes': nuevos_usuarios_mes,
    }

class ReporteUsuariosView(AdminOrStaffRequiredMixin, TemplateView):
    """
    Módulo 4: Reportes de usuarios.
    """
    template_name = 'panel/reportes/reporte_usuarios.html'

    ORDEN_OPCIONES = {
        'nombre': 'full_name',
        'fecha': '-date_joined',
        'inscripciones': '-num_inscripciones',
        'pruebas': '-num_pruebas',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # --- Filtros ---
        rol = request.GET.get('rol', 'todos')  # sistema | directivo | instructor | estudiante | todos
        estado = request.GET.get('estado', 'todos')  # activo | inactivo | todos
        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        q = request.GET.get('q', '').strip()
        orden = request.GET.get('orden', 'nombre')
        page_num = request.GET.get('page', 1)

        usuarios_qs = CustomUser.objects.all()

        if rol == 'sistema':
            usuarios_qs = usuarios_qs.filter(is_staff=True)
        elif rol == 'directivo':
            usuarios_qs = usuarios_qs.filter(is_staff=False, groups__name=GRUPO_DIRECTIVO)
        elif rol == 'instructor':
            usuarios_qs = usuarios_qs.filter(is_staff=False, groups__name=GRUPO_INSTRUCTORES).exclude(groups__name=GRUPO_DIRECTIVO)
        elif rol == 'estudiante':
            usuarios_qs = usuarios_qs.filter(is_staff=False).exclude(
                groups__name__in=[GRUPO_DIRECTIVO, GRUPO_INSTRUCTORES]
            )

        if estado == 'activo':
            usuarios_qs = usuarios_qs.filter(is_active=True)
        elif estado == 'inactivo':
            usuarios_qs = usuarios_qs.filter(is_active=False)

        if desde:
            desde_dt = timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d'))
            usuarios_qs = usuarios_qs.filter(date_joined__gte=desde_dt)
        if hasta:
            hasta_dt = timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            usuarios_qs = usuarios_qs.filter(date_joined__lte=hasta_dt)

        if q:
            usuarios_qs = usuarios_qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q) | Q(username__icontains=q))

        usuarios_qs = usuarios_qs.distinct().annotate(
            num_inscripciones=Count('inscripciones', distinct=True),
        )

        # --- Resumen general (sobre el total de usuarios, sin filtros, para que el panorama no cambie con la búsqueda) ---
        datos = _get_usuarios_resumen_data()

        # --- Tabla detallada (con número de pruebas, calculado aparte porque son 2 modelos) ---
        pruebas_allport_por_usuario = dict(
            ResultadoValores.objects.values('usuario_id').annotate(total=Count('id')).values_list('usuario_id', 'total')
        )
        pruebas_domino_por_usuario = dict(
            ResultadoDomino.objects.values('usuario_id').annotate(total=Count('id')).values_list('usuario_id', 'total')
        )

        filas = []
        for u in usuarios_qs:
            es_admin = u.is_staff
            es_directivo = not es_admin and u.groups.filter(name=GRUPO_DIRECTIVO).exists()
            es_instructor = not es_admin and not es_directivo and u.groups.filter(name=GRUPO_INSTRUCTORES).exists()
            rol_texto = 'Administrador del Sistema' if es_admin else 'Directivo / Coordinador' if es_directivo else 'Instructor' if es_instructor else 'Estudiante'

            num_pruebas = pruebas_allport_por_usuario.get(u.id, 0) + pruebas_domino_por_usuario.get(u.id, 0)
            filas.append({
                'usuario': u,
                'rol': rol_texto,
                'num_inscripciones': u.num_inscripciones,
                'num_pruebas': num_pruebas,
            })

        orden_field = orden
        if orden == 'inscripciones':
            filas.sort(key=lambda f: f['num_inscripciones'], reverse=True)
        elif orden == 'pruebas':
            filas.sort(key=lambda f: f['num_pruebas'], reverse=True)
        elif orden == 'fecha':
            filas.sort(key=lambda f: f['usuario'].date_joined, reverse=True)
        else:
            filas.sort(key=lambda f: (f['usuario'].full_name or '').lower())

        paginator = Paginator(filas, 20)
        page_obj = paginator.get_page(page_num)

        context.update({
            **datos,
            'titulo_pagina': 'Reporte de usuarios',
            'rol': rol,
            'estado': estado,
            'desde': desde,
            'hasta': hasta,
            'q': q,
            'orden': orden,
            'page_obj': page_obj,
        })
        return context

@login_required
def generar_pdf_usuarios(request):
    user = request.user
    if not (user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()):
        raise PermissionDenied("Se requieren permisos de administrador para esta acción.")

    datos = _get_usuarios_resumen_data()
    dorado, salvia, arena, calido, rojo = '#a08848', '#709888', '#d8c898', '#c09060', '#b05050'

    dr = datos['distribucion_rol']
    plt.figure(figsize=(4.5, 4.5), facecolor='white')
    plt.pie(dr['data'], labels=dr['labels'], autopct='%1.0f%%', colors=[dorado, calido, salvia, arena])
    plt.title('Distribución por rol', fontsize=12, fontweight='bold')
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_rol = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    ai = datos['activos_inactivos']
    plt.figure(figsize=(4, 4), facecolor='white')
    plt.pie(ai['data'], labels=ai['labels'], autopct='%1.0f%%', colors=[salvia, rojo])
    plt.title('Activos vs inactivos', fontsize=12, fontweight='bold')
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_activos = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    nu = datos['nuevos_usuarios_mes']
    plt.figure(figsize=(8, 4), facecolor='white')
    plt.plot(nu['labels'], nu['data'], color=dorado, marker='o')
    plt.xticks(rotation=45, ha='right', fontsize=8)
    plt.title('Nuevos usuarios por mes', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_nuevos = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    context = {
        **datos,
        'grafico_rol': grafico_rol,
        'grafico_activos': grafico_activos,
        'grafico_nuevos': grafico_nuevos,
        'logo_base64': _get_logo_base64(),
        'fecha_generacion': timezone.now(),
    }

    template = get_template('panel/reportes/pdf/usuarios_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_usuarios_centro_dhae.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response

def _get_comparativos_data(desde_dt, hasta_dt):
    """Datos del Módulo 5, compartido entre la vista HTML y el PDF."""
    GENERO_LABELS = dict(CustomUser.GENDER_CHOICES)

    # 1. Pruebas por género
    allport_genero = dict(
        ResultadoValores.objects.filter(fecha_completado__range=(desde_dt, hasta_dt))
        .values('usuario__gender').annotate(total=Count('id')).values_list('usuario__gender', 'total')
    )
    domino_genero = dict(
        ResultadoDomino.objects.filter(fecha__range=(desde_dt, hasta_dt))
        .values('usuario__gender').annotate(total=Count('id')).values_list('usuario__gender', 'total')
    )
    generos = sorted(set(allport_genero) | set(domino_genero), key=lambda g: g or '')
    comparativo_genero = {
        'labels': [GENERO_LABELS.get(g, 'Sin especificar') for g in generos],
        'allport': [allport_genero.get(g, 0) for g in generos],
        'domino': [domino_genero.get(g, 0) for g in generos],
    }

    # 2. Percentil promedio por grupo de edad (Dominó)
    percentil_edad = (ResultadoDomino.objects.filter(fecha__range=(desde_dt, hasta_dt))
                       .values('grupo_edad').annotate(promedio=Avg('percentil'), total=Count('id')).order_by('-promedio'))
    promedio_general_percentil = ResultadoDomino.objects.filter(
        fecha__range=(desde_dt, hasta_dt)
    ).aggregate(p=Avg('percentil'))['p'] or 0

    tabla_edad = []
    for e in percentil_edad:
        promedio = e['promedio'] or 0
        variacion = round((promedio - promedio_general_percentil) / promedio_general_percentil * 100, 1) if promedio_general_percentil else 0
        tabla_edad.append({'grupo_edad': e['grupo_edad'] or 'Sin especificar', 'promedio_percentil': round(promedio, 1), 'total': e['total'], 'variacion': variacion})

    # 3. Tasa de finalización por institución
    inscripciones_qs = Inscripcion.objects.filter(inscrito_en__range=(desde_dt, hasta_dt)).exclude(
        estudiante__institution__isnull=True
    ).exclude(estudiante__institution='')

    por_institucion = {}
    for i in inscripciones_qs.values('estudiante__institution').annotate(
        total=Count('id'), completadas=Count('id', filter=Q(completado=True))
    ):
        por_institucion[i['estudiante__institution']] = i

    total_inscripciones_gen = inscripciones_qs.count()
    completadas_gen = inscripciones_qs.filter(completado=True).count()
    tasa_general = round(completadas_gen / total_inscripciones_gen * 100, 1) if total_inscripciones_gen else 0

    tabla_institucion = []
    for inst, dt in sorted(por_institucion.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
        tasa = round(dt['completadas'] / dt['total'] * 100, 1) if dt['total'] else 0
        tabla_institucion.append({'institucion': inst, 'total': dt['total'], 'completadas': dt['completadas'], 'tasa_finalizacion': tasa, 'variacion': round(tasa - tasa_general, 1)})

    # 4. Progreso promedio por instructor
    progreso_instructor = (Inscripcion.objects.filter(inscrito_en__range=(desde_dt, hasta_dt), curso__instructor__isnull=False)
                            .values('curso__instructor__full_name').annotate(promedio=Avg('progreso'), total=Count('id')).order_by('-promedio'))
    promedio_general_progreso = Inscripcion.objects.filter(
        inscrito_en__range=(desde_dt, hasta_dt)
    ).aggregate(p=Avg('progreso'))['p'] or 0

    tabla_instructor = []
    for p in progreso_instructor:
        promedio = p['promedio'] or 0
        tabla_instructor.append({
            'instructor': p['curso__instructor__full_name'], 'progreso_promedio': round(promedio, 1),
            'total_estudiantes': p['total'], 'variacion': round(promedio - promedio_general_progreso, 1),
        })

    return {
        'comparativo_genero': comparativo_genero,
        'tabla_edad': tabla_edad,
        'tabla_institucion': tabla_institucion,
        'tabla_instructor': tabla_instructor,
    }

class ReporteComparativosView(AdminOrStaffRequiredMixin, TemplateView):
    """
    Módulo 5: Reportes comparativos.
    """
    template_name = 'panel/reportes/reporte_comparativos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        hoy = timezone.now()
        hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
                    if hasta else hoy)
        desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d'))
                    if desde else hoy - timedelta(days=365))

        datos = _get_comparativos_data(desde_dt, hasta_dt)

        context.update({
            **datos,
            'titulo_pagina': 'Reportes comparativos',
            'desde': desde_dt.date(),
            'hasta': hasta_dt.date(),
        })
        return context

import numpy as np

@login_required
def generar_pdf_comparativos(request):
    user = request.user
    if not (user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()):
        raise PermissionDenied("Se requieren permisos de administrador para esta acción.")

    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    hoy = timezone.now()
    hasta_dt = (timezone.make_aware(timezone.datetime.strptime(hasta, '%Y-%m-%d').replace(hour=23, minute=59, second=59)) if hasta else hoy)
    desde_dt = (timezone.make_aware(timezone.datetime.strptime(desde, '%Y-%m-%d')) if desde else hoy - timedelta(days=365))

    datos = _get_comparativos_data(desde_dt, hasta_dt)
    dorado, salvia = '#a08848', '#709888'

    cg = datos['comparativo_genero']
    x = np.arange(len(cg['labels']))
    ancho = 0.35
    plt.figure(figsize=(7, 4), facecolor='white')
    plt.bar(x - ancho/2, cg['allport'], ancho, label='Allport', color=dorado)
    plt.bar(x + ancho/2, cg['domino'], ancho, label='Dominó', color=salvia)
    plt.xticks(x, cg['labels'])
    plt.legend()
    plt.title('Pruebas aplicadas por género', fontsize=12, fontweight='bold')
    plt.tight_layout()
    buffer = BytesIO(); plt.savefig(buffer, format='png', bbox_inches='tight'); plt.close(); buffer.seek(0)
    grafico_genero = base64.b64encode(buffer.getvalue()).decode('utf-8'); buffer.close()

    context = {
        **datos,
        'grafico_genero': grafico_genero,
        'logo_base64': _get_logo_base64(),
        'desde': desde_dt.date(),
        'hasta': hasta_dt.date(),
        'fecha_generacion': timezone.now(),
    }

    template = get_template('panel/reportes/pdf/comparativos_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_comparativos_centro_dhae.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response