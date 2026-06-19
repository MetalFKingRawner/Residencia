from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from ckeditor.fields import RichTextField
from embed_video.fields import EmbedVideoField
from django.core.exceptions import ValidationError

from users.models import CustomUser


class Curso(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título")
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name="Slug")
    descripcion = RichTextField(verbose_name="Descripción")
    imagen = models.ImageField(
        upload_to="cursos/portadas/",
        blank=True,
        null=True,
        verbose_name="Imagen de portada"
    )
    instructor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cursos_impartidos",
        verbose_name="Instructor"
    )
    publicado = models.BooleanField(default=False, verbose_name="Publicado")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ["-creado_en"]
        permissions = [
            ("puede_ver_todos_cursos", "Puede ver todos los cursos"),
            ("puede_asignar_instructores", "Puede asignar instructores"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)
            slug = base_slug
            contador = 1

            while Curso.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{contador}"
                contador += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo


class Leccion(models.Model):
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="lecciones"
    )
    titulo = models.CharField(max_length=200, verbose_name="Título")
    orden = models.PositiveIntegerField(verbose_name="Orden")
    vista_previa_gratis = models.BooleanField(default=False, verbose_name="Vista previa gratuita")

    class Meta:
        verbose_name = "Lección"
        verbose_name_plural = "Lecciones"
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["curso", "orden"],
                name="unique_orden_por_curso"
            )
        ]

    def __str__(self):
        return f"{self.curso.titulo} - {self.titulo}"

class RecursoLeccion(models.Model):
    TIPOS_RECURSO = [
        ('texto', 'Texto / Lectura'),
        ('video', 'Video Embebido'),
        ('archivo', 'Documento Descargable (PDF/Word)'),
        ('audio', 'Audio (MP3/Podcast)'),
    ]

    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE, related_name="recursos")
    tipo = models.CharField(max_length=10, choices=TIPOS_RECURSO)
    orden = models.PositiveIntegerField(default=1)
    
    # Campos específicos (quedarán vacíos según el tipo de recurso)
    contenido_texto = RichTextField(blank=True, null=True)
    video_url = EmbedVideoField(blank=True, null=True)
    archivo = models.FileField(upload_to="lecciones/recursos/", blank=True, null=True)

    class Meta:
        ordering = ["orden"]

    def clean(self):
        if self.tipo == 'texto' and not self.contenido_texto:
            raise ValidationError('El recurso de texto necesita contenido')
        if self.tipo == 'video' and not self.video_url:
            raise ValidationError('El recurso de video necesita una URL')
        if self.tipo in ('archivo', 'audio') and not self.archivo:
            raise ValidationError(f'El recurso {self.get_tipo_display()} necesita un archivo')
        # Evitar campos redundantes
        if self.tipo != 'texto' and self.contenido_texto:
            raise ValidationError('Solo los recursos de texto pueden tener contenido_texto')
        if self.tipo != 'video' and self.video_url:
            raise ValidationError('Solo los recursos de video pueden tener video_url')
        if self.tipo not in ('archivo', 'audio') and self.archivo:
            raise ValidationError('Solo archivo o audio pueden tener archivo')

    def __str__(self):
        return f"{self.leccion.titulo} - {self.get_tipo_display()} ({self.orden})"

class Inscripcion(models.Model):
    estudiante = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="inscripciones",
        verbose_name="Estudiante"
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="inscripciones",
        verbose_name="Curso"
    )
    inscrito_en = models.DateTimeField(auto_now_add=True, verbose_name="Inscrito el")
    completado = models.BooleanField(default=False, verbose_name="Completado")
    certificado_generado = models.BooleanField(default=False, verbose_name="Certificado generado")
    progreso = models.PositiveSmallIntegerField(default=0, verbose_name="Progreso (%)")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "curso"],
                name="unique_estudiante_curso"
            ),
            models.CheckConstraint(
                check=Q(progreso__gte=0) & Q(progreso__lte=100),
                name="progreso_entre_0_y_100"
            )
        ]

    def __str__(self):
        return f"{self.estudiante.username} - {self.curso.titulo}"
    

class LeccionCompletada(models.Model):
    inscripcion = models.ForeignKey(
        'Inscripcion',  # como Inscripción está después, usamos string
        on_delete=models.CASCADE,
        related_name='lecciones_completadas'
    )
    leccion = models.ForeignKey(
        Leccion,
        on_delete=models.CASCADE,
        related_name='completada_por'
    )
    completada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('inscripcion', 'leccion')  # evita duplicados
        verbose_name = "Lección completada"
        verbose_name_plural = "Lecciones completadas"

    def __str__(self):
        return f"{self.inscripcion.estudiante.username} - {self.leccion.titulo}"