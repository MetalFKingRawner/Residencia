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
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io, os
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

        todas_lecciones = curso.lecciones.order_by('orden')
        context['recursos'] = leccion.recursos.all().order_by('orden')
        context['curso'] = curso
        context['todas_lecciones'] = todas_lecciones

        # Navegación anterior / siguiente
        context['leccion_anterior'] = todas_lecciones.filter(orden__lt=leccion.orden).last()
        context['leccion_siguiente'] = todas_lecciones.filter(orden__gt=leccion.orden).first()

        user_inscrito = False
        leccion_completada = False
        lecciones_completadas_ids = set()
        progreso = None

        if user.is_authenticated:
            inscripcion = Inscripcion.objects.filter(estudiante=user, curso=curso).first()
            if inscripcion:
                user_inscrito = True
                leccion_completada = LeccionCompletada.objects.filter(
                    inscripcion=inscripcion,
                    leccion=leccion
                ).exists()

                completadas = LeccionCompletada.objects.filter(
                    inscripcion=inscripcion
                ).values_list('leccion__orden', flat=True)
                lecciones_completadas_ids = set(completadas)
                progreso = inscripcion.progreso

        context['user_inscrito'] = user_inscrito
        context['leccion_completada'] = leccion_completada
        context['lecciones_completadas_ids'] = lecciones_completadas_ids
        context['progreso'] = progreso
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

STATIC = os.path.join(settings.BASE_DIR, 'static')
    
def descargar_certificado(request, slug):
    curso = get_object_or_404(Curso, slug=slug, publicado=True)

    try:
        inscripcion = Inscripcion.objects.select_related(
            'estudiante', 'curso__instructor'
        ).get(estudiante=request.user, curso=curso)
    except Inscripcion.DoesNotExist:
        return HttpResponse("No estás inscrito en este curso.", status=403)

    if inscripcion.progreso < 100:
        return HttpResponse("Aún no has completado el curso.", status=403)

    if not inscripcion.certificado_generado:
        inscripcion.certificado_generado = True
        inscripcion.save(update_fields=['certificado_generado'])

    nombre            = inscripcion.estudiante.full_name or inscripcion.estudiante.username
    instructor        = curso.instructor
    instructor_nombre = instructor.full_name if instructor else "Centro DHAE"

    meses = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
             7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
    hoy       = date.today()
    fecha_str = f"{hoy.day} de {meses[hoy.month]} de {hoy.year}"

    # ── Rutas de recursos ──────────────────────────────────────────
    ruta_fondo  = os.path.join(STATIC, 'img',   'sello-dorado.png')
    ruta_sello  = os.path.join(STATIC, 'img',   'sello-medalla.png')
    ruta_firma  = os.path.join(STATIC, 'fonts', 'GreatVibes-Regular.ttf')
    ruta_normal = os.path.join(STATIC, 'fonts', 'Lora-Regular.ttf')

    # ── Abrir fondo ────────────────────────────────────────────────
    img  = Image.open(ruta_fondo).convert('RGBA')
    W, H = img.size
    draw = ImageDraw.Draw(img)

    # ── Factor de escala (referencia: 850 px de ancho) ─────────────
    escala = W / 850

    # ── Colores ────────────────────────────────────────────────────
    COLOR_OSCURO = (32,  24,   8)
    COLOR_DORADO = (107, 83,  30)
    COLOR_GRIS   = (100, 100, 100)
    COLOR_FIRMA  = (51,  51,  51)
    COLOR_ORO    = (184, 151,  66)

    # ── Grosores escalados ─────────────────────────────────────────
    LINEA_FINA   = max(1, int(1 * escala))
    LINEA_GRUESA = max(2, int(2 * escala))
    ROMBO_R      = int(5 * escala)

    def fuente(ruta, pt):
        try:
            return ImageFont.truetype(ruta, pt)
        except:
            for sistema in [
                '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
            ]:
                try:
                    return ImageFont.truetype(sistema, pt)
                except:
                    continue
            return ImageFont.load_default()

    def centrar_x(texto, fuente_obj, y, color):
        bbox = draw.textbbox((0, 0), texto, font=fuente_obj)
        tw   = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), texto, font=fuente_obj, fill=color)

    def alto_texto(texto, fuente_obj):
        bbox = draw.textbbox((0, 0), texto, font=fuente_obj)
        return bbox[3] - bbox[1]

    # ── Tipografías ────────────────────────────────────────────────
    f_titulo       = fuente(ruta_normal, int(50 * escala))
    f_subtitulo    = fuente(ruta_normal, int(18 * escala))
    f_intro        = fuente(ruta_normal, int(16 * escala))
    f_nombre       = fuente(ruta_firma,  int(78 * escala))  # un poco más pequeño
    f_curso        = fuente(ruta_normal, int(18 * escala))  # más pequeño
    f_reconoc      = fuente(ruta_normal, int(15 * escala))
    f_firma_nombre = fuente(ruta_normal, int(15 * escala))  # más pequeño
    f_firma_rol    = fuente(ruta_normal, int(13 * escala))
    f_fecha        = fuente(ruta_normal, int(13 * escala))

    # ══════════════════════════════════════════════════════════════
    #  LAYOUT
    # ══════════════════════════════════════════════════════════════

    # 1. Título — arranca un poco más abajo del borde dorado
    y = int(H * 0.10)
    centrar_x("CERTIFICADO", f_titulo, y, COLOR_DORADO)

    # 2. Subtítulo — pegado al título, sin tanto espacio
    y += alto_texto("CERTIFICADO", f_titulo) + int(20 * escala)
    centrar_x("DE PARTICIPACIÓN", f_subtitulo, y, COLOR_DORADO)

    # Línea decorativa delgada bajo el subtítulo
    y_linea1 = y + alto_texto("DE PARTICIPACIÓN", f_subtitulo) + int(18 * escala)
    linea_dec_w = int(W * 0.30)
    lx0 = (W - linea_dec_w) // 2
    draw.line([(lx0, y_linea1), (lx0 + linea_dec_w, y_linea1)], fill=COLOR_ORO, width=LINEA_FINA)

    # 3. "Este certificado se otorga a:"
    y = y_linea1 + int(40 * escala)
    centrar_x("Este certificado se otorga a:", f_intro, y, COLOR_GRIS)

    # 4. Nombre del estudiante — tamaño adaptativo
    MAX_NOMBRE_W = int(W * 0.68)  # ancho máximo permitido (dentro del marco)
    pt_nombre = int(78 * escala)  # tamaño inicial

    # Reducir hasta que quepa
    while pt_nombre > int(30 * escala):
        f_nombre = fuente(ruta_firma, pt_nombre)
        bbox_test = draw.textbbox((0, 0), nombre, font=f_nombre)
        if (bbox_test[2] - bbox_test[0]) <= MAX_NOMBRE_W:
            break
        pt_nombre -= int(2 * escala)  # bajar de 2 en 2 pt

    y += alto_texto("Este certificado se otorga a:", f_intro) + int(18 * escala)
    centrar_x(nombre, f_nombre, y, COLOR_OSCURO)

    # Línea bajo el nombre
    bbox_n    = draw.textbbox((0, 0), nombre, font=f_nombre)
    nombre_h  = bbox_n[3] - bbox_n[1]
    nombre_w  = bbox_n[2] - bbox_n[0]
    linea_n_w = min(int(nombre_w * 1.08), int(W * 0.58))
    lx_n0     = (W - linea_n_w) // 2
    ly_n      = y + nombre_h + int(8 * escala)
    draw.line([(lx_n0, ly_n), (lx_n0 + linea_n_w, ly_n)], fill=COLOR_ORO, width=LINEA_GRUESA)

    # 5. Texto de reconocimiento
    y = ly_n + int(22 * escala)
    centrar_x(
        "en reconocimiento por su valiosa participación y conclusión satisfactoria del curso:",
        f_reconoc, y, COLOR_GRIS
    )

    # 6. Nombre del curso
    y += alto_texto("en reconocimiento...", f_reconoc) + int(16 * escala)
    palabras = curso.titulo.split()
    if len(palabras) > 5:
        mitad  = len(palabras) // 2
        linea1 = " ".join(palabras[:mitad])
        linea2 = " ".join(palabras[mitad:])
    else:
        linea1, linea2 = curso.titulo, ""

    centrar_x(linea1, f_curso, y, COLOR_FIRMA)
    if linea2:
        y += alto_texto(linea1, f_curso) + int(6 * escala)
        centrar_x(linea2, f_curso, y, COLOR_FIRMA)

    # ══════════════════════════════════════════════════════════════
    #  FIRMAS — fijas desde el fondo con más espacio
    # ══════════════════════════════════════════════════════════════
    y_firma  = int(H * 0.77)
    linea_fw = int(W * 0.18)

    # Firma izquierda
    fx_izq = int(W * 0.16)
    draw.line([(fx_izq, y_firma), (fx_izq + linea_fw, y_firma)], fill=COLOR_ORO, width=LINEA_FINA)
    centrar_texto_en(draw, "Alba Castro", f_firma_nombre, fx_izq, linea_fw, y_firma + int(10 * escala), COLOR_FIRMA)
    centrar_texto_en(draw, "Dirección",   f_firma_rol,    fx_izq, linea_fw, y_firma + int(34 * escala), COLOR_GRIS)

    # Firma derecha
    fx_der = int(W * 0.66)
    draw.line([(fx_der, y_firma), (fx_der + linea_fw, y_firma)], fill=COLOR_ORO, width=LINEA_FINA)
    centrar_texto_en(draw, instructor_nombre, f_firma_nombre, fx_der, linea_fw, y_firma + int(10 * escala), COLOR_FIRMA)
    centrar_texto_en(draw, "Instructor",      f_firma_rol,    fx_der, linea_fw, y_firma + int(34 * escala), COLOR_GRIS)

    # Rombo decorativo central entre las dos firmas
    cx = W // 2
    cy = y_firma
    draw.polygon(
        [(cx, cy - ROMBO_R), (cx + ROMBO_R, cy),
         (cx, cy + ROMBO_R), (cx - ROMBO_R, cy)],
        fill=COLOR_ORO
    )

    # Sello central (opcional)
    try:
        sello_size = int(110 * escala)
        sello = Image.open(ruta_sello).convert('RGBA')
        sello = sello.resize((sello_size, sello_size), Image.LANCZOS)
        sx = (W - sello_size) // 2
        img.paste(sello, (sx, y_firma - int(50 * escala)), sello)
    except FileNotFoundError:
        pass

    # Fecha
    centrar_x(fecha_str, f_fecha, int(H * 0.87), COLOR_DORADO)

    # ══════════════════════════════════════════════════════════════
    #  EXPORTAR A PDF
    # ══════════════════════════════════════════════════════════════
    img_rgb    = img.convert('RGB')
    img_buffer = io.BytesIO()
    img_rgb.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(841.89, 595.28))
    c.drawImage(ImageReader(img_buffer), 0, 0, width=841.89, height=595.28)
    c.save()

    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="certificado_{slug}.pdf"'
    return response


def centrar_texto_en(draw, texto, fuente_obj, x_inicio, ancho, y, color):
    bbox = draw.textbbox((0, 0), texto, font=fuente_obj)
    tw   = bbox[2] - bbox[0]
    draw.text((x_inicio + (ancho - tw) / 2, y), texto, font=fuente_obj, fill=color)