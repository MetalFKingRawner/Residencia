from django.views.generic import ListView, DetailView
from .models import Curso, Leccion, Inscripcion, LeccionCompletada
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from .forms import SolicitudAccesoForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

class CursoListView(ListView):
    model = Curso
    template_name = 'courses/home.html'
    context_object_name = 'cursos'
    queryset = Curso.objects.filter(publicado=True)
    ordering = ['-creado_en']

class CursoDetailView(DetailView):
    model = Curso
    template_name = 'courses/course_detail.html'
    context_object_name = 'curso'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.object
        user = self.request.user

        lecciones = curso.lecciones.prefetch_related('recursos').order_by('orden')
        context['lecciones'] = lecciones

        user_inscrito = False
        progreso = 0
        lecciones_completadas_ids = []

        if user.is_authenticated:
            inscripcion = Inscripcion.objects.filter(estudiante=user, curso=curso).first()
            if inscripcion:
                user_inscrito = True
                completadas = LeccionCompletada.objects.filter(
                    inscripcion=inscripcion
                ).values_list('leccion_id', flat=True)
                lecciones_completadas_ids = list(completadas)

                total_lecciones = lecciones.count()
                if total_lecciones > 0:
                    progreso = int((len(lecciones_completadas_ids) / total_lecciones) * 100)
                else:
                    progreso = 0

                if inscripcion.progreso != progreso:
                    inscripcion.progreso = progreso
                    inscripcion.save(update_fields=['progreso'])

        context['user_inscrito'] = user_inscrito
        context['progreso'] = progreso
        context['lecciones_completadas_ids'] = lecciones_completadas_ids

        return context

class CursoCatalogoView(ListView):
    model = Curso
    template_name = 'courses/courses_list.html'
    context_object_name = 'cursos'
    queryset = Curso.objects.filter(publicado=True)
    ordering = ['-creado_en']

class LeccionDetailView(DetailView):
    model = Leccion
    template_name = 'courses/leccion_detalle.html'   # crearemos este template después
    context_object_name = 'leccion'
    
    def get_object(self):
        curso_slug = self.kwargs.get('slug')
        orden = self.kwargs.get('orden')
        curso = get_object_or_404(Curso, slug=curso_slug)
        return get_object_or_404(
            Leccion.objects.prefetch_related('recursos'), 
            curso=curso, 
            orden=orden
        )
        
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        leccion = self.object
        curso = leccion.curso
        user = request.user

        puede_ver = False

        if leccion.vista_previa_gratis:
            puede_ver = True
        elif user.is_authenticated:
            inscripcion = Inscripcion.objects.filter(estudiante=user, curso=curso).first()
            if inscripcion:
                lecciones_anteriores = curso.lecciones.filter(orden__lt=leccion.orden)
                completadas_anteriores = LeccionCompletada.objects.filter(
                    inscripcion=inscripcion,
                    leccion__in=lecciones_anteriores
                ).count()
                puede_ver = (completadas_anteriores == lecciones_anteriores.count())

                if not puede_ver:
                    messages.warning(request, "Completa las lecciones anteriores primero.")

        if not puede_ver:
            messages.error(request, "No tienes acceso a esta lección.")
            return redirect('courses:curso_detail', slug=curso.slug)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leccion = self.object
        curso = leccion.curso
        user = self.request.user

        context['recursos'] = leccion.recursos.all().order_by('orden')
        context['curso'] = curso

        user_inscrito = False
        leccion_completada = False

        if user.is_authenticated:
            inscripcion = Inscripcion.objects.filter(estudiante=user, curso=curso).first()
            if inscripcion:
                user_inscrito = True
                leccion_completada = LeccionCompletada.objects.filter(
                    inscripcion=inscripcion,
                    leccion=leccion
                ).exists()

        context['user_inscrito'] = user_inscrito
        context['leccion_completada'] = leccion_completada
        context['puede_ver'] = True

        return context
    
@login_required
def completar_leccion(request, slug, orden):
    if request.method != 'POST':
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    curso = get_object_or_404(Curso, slug=slug)
    leccion = get_object_or_404(Leccion, curso=curso, orden=orden)
    inscripcion = get_object_or_404(Inscripcion, estudiante=request.user, curso=curso)

    LeccionCompletada.objects.get_or_create(
        inscripcion=inscripcion,
        leccion=leccion
    )

    total = curso.lecciones.count()
    completadas = LeccionCompletada.objects.filter(inscripcion=inscripcion).count()
    inscripcion.progreso = int((completadas / total) * 100) if total > 0 else 0

    if inscripcion.progreso == 100:
        inscripcion.completado = True

    inscripcion.save(update_fields=['progreso', 'completado'])

    messages.success(request, f'¡Lección "{leccion.titulo}" marcada como completada!')
    return redirect('courses:leccion_detail', slug=curso.slug, orden=leccion.orden)

def solicitar_acceso(request, slug):
    curso = get_object_or_404(Curso, slug=slug)
    
    if request.method == 'POST':
        form = SolicitudAccesoForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data.get('telefono', '')
            mensaje_extra = form.cleaned_data.get('mensaje', '')
            
            asunto = f"Solicitud de acceso al curso: {curso.titulo}"
            mensaje = f"""
            El usuario {nombre} ({email}) solicita acceso al curso "{curso.titulo}".
            Teléfono: {telefono if telefono else 'No proporcionado'}
            
            Mensaje adicional:
            {mensaje_extra if mensaje_extra else 'Ninguno'}
            """
            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            messages.success(request, 'Solicitud enviada. Pronto te contactaremos.')
            return redirect('courses:curso_detail', slug=curso.slug)
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        return redirect('courses:curso_detail', slug=curso.slug)
    
def certificado_pendiente(request, slug):
    return HttpResponse(
        "El certificado para este curso estara disponible proximamente.",
        content_type="text/plain"
    )