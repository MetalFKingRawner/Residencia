from django.db import models
from django.core.exceptions import ValidationError

class ConfiguracionPlataforma(models.Model):
    registro_abierto = models.BooleanField(
        default=False, 
        verbose_name="Registro de Estudiantes Abierto (Landing/Cursos)"
    )
    pruebas_activas = models.BooleanField(
        default=False, 
        verbose_name="Plataforma de Pruebas Activa (Login/Métrica)"
    )

    class Meta:
        verbose_name = "Configuración de Plataforma"
        verbose_name_plural = "Configuración Global"

    def save(self, *args, **kwargs):
        # Evitar que se cree más de una fila de configuración
        if not self.pk and ConfiguracionPlataforma.objects.exists():
            raise ValidationError('Solo puede existir una configuración global en el sistema.')
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Configuración Activa del Sistema"