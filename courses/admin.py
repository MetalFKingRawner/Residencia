from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Curso, Leccion, Inscripcion, LeccionCompletada, RecursoLeccion

CustomUser = get_user_model()

# Filtro para mostrar solo instructores (usuarios con permiso específico o is_staff)
# Ajusta según tu lógica: podrías tener un campo 'es_instructor' en CustomUser
# Por ahora, asumimos que los instructores son usuarios con is_staff=True
def instructores_queryset(request):
    return CustomUser.objects.filter(is_staff=True)  # o filtra por grupo "Instructor"

class RecursoLeccionInline(admin.TabularInline):
    model = RecursoLeccion
    extra = 1
    fields = ('tipo', 'orden', 'contenido_texto', 'video_url', 'archivo')
    ordering = ('orden',)

class LeccionInline(admin.TabularInline):
    model = Leccion
    extra = 1
    fields = ('titulo', 'orden', 'vista_previa_gratis')
    ordering = ('orden',)

class LeccionCompletadaInline(admin.TabularInline):
    model = LeccionCompletada
    extra = 0
    readonly_fields = ('completada_en',)
    fields = ('leccion', 'completada_en')
    can_delete = True
    show_change_link = False

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'instructor', 'publicado', 'creado_en', 'actualizado_en')
    list_filter = ('publicado', 'creado_en', 'instructor')
    search_fields = ('titulo', 'descripcion')
    prepopulated_fields = {'slug': ('titulo',)}
    raw_id_fields = ('instructor',)  # si hay muchos usuarios, mejor raw_id
    actions = ['publicar_cursos', 'despublicar_cursos']
    inlines = [LeccionInline]

    fieldsets = (
        (None, {
            'fields': ('titulo', 'slug', 'descripcion', 'imagen', 'instructor')
        }),
        ('Estado', {
            'fields': ('publicado',),
            'classes': ('collapse',)
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'instructor':
            # Limitar a usuarios que pueden ser instructores (staff o grupo específico)
            kwargs['queryset'] = CustomUser.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def publicar_cursos(self, request, queryset):
        queryset.update(publicado=True)
    publicar_cursos.short_description = "Publicar cursos seleccionados"

    def despublicar_cursos(self, request, queryset):
        queryset.update(publicado=False)
    despublicar_cursos.short_description = "Despublicar cursos seleccionados"

@admin.register(Leccion)
class LeccionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'orden', 'vista_previa_gratis')
    list_filter = ('curso', 'vista_previa_gratis')
    search_fields = ('titulo',)
    ordering = ('curso', 'orden')
    raw_id_fields = ('curso',)
    inlines = [RecursoLeccionInline]

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'curso', 'inscrito_en', 'progreso', 'completado', 'certificado_generado')
    list_filter = ('completado', 'certificado_generado', 'curso', 'inscrito_en')
    search_fields = ('estudiante__username', 'estudiante__email', 'curso__titulo')
    raw_id_fields = ('estudiante', 'curso')
    readonly_fields = ('inscrito_en',)
    actions = ['marcar_completado', 'generar_certificado']
    inlines = [LeccionCompletadaInline]

    fieldsets = (
        (None, {
            'fields': ('estudiante', 'curso')
        }),
        ('Progreso', {
            'fields': ('progreso', 'completado', 'certificado_generado')
        }),
        ('Fechas', {
            'fields': ('inscrito_en',),
            'classes': ('collapse',)
        }),
    )

    def marcar_completado(self, request, queryset):
        queryset.update(completado=True, progreso=100)
    marcar_completado.short_description = "Marcar cursos como completados al 100%%"

    def generar_certificado(self, request, queryset):
        # Acción placeholder para generar certificados manualmente
        for insc in queryset:
            if insc.completado and not insc.certificado_generado:
                insc.certificado_generado = True
                insc.save()
                # Llamar a tu función de generación de PDF aquí
        self.message_user(request, f"Certificados generados para {queryset.count()} inscripciones.")
    generar_certificado.short_description = "Generar certificado para inscripciones completadas"

@admin.register(LeccionCompletada)
class LeccionCompletadaAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'leccion', 'completada_en')
    list_filter = ('completada_en', 'leccion__curso')
    search_fields = ('inscripcion__estudiante__username', 'leccion__titulo')
    raw_id_fields = ('inscripcion', 'leccion')
    readonly_fields = ('completada_en',)