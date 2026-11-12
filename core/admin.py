# core/admin.py
from django.contrib import admin
from .models import ConfiguracionPlataforma

@admin.register(ConfiguracionPlataforma)
class ConfiguracionPlataformaAdmin(admin.ModelAdmin):
    # Columnas que se verán en la lista principal (aunque solo sea una fila)
    list_display = ('__str__', 'registro_abierto', 'pruebas_activas')
    
    # Permitir editar los checkboxes directamente desde la lista sin entrar al registro
    list_editable = ('registro_abierto', 'pruebas_activas')

    def has_add_permission(self, request):
        # Si ya existe al menos una configuración, escondemos el botón "Añadir"
        if ConfiguracionPlataforma.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Opcional: Impedir que se borre la configuración por accidente desde el admin
        return False