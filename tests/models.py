# tests/models.py
from django.db import models
from users.models import CustomUser
from django.conf import settings
import json

class TestValores(models.Model):
    nombre = models.CharField(max_length=200)
    autor = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.nombre
    
class ParteTest(models.Model):
    TIPO_PARTE = [
        ('PRIMERA', 'Primera Parte'),
        ('SEGUNDA', 'Segunda Parte'),
    ]
    
    test = models.ForeignKey(TestValores, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_PARTE)
    instrucciones = models.TextField()
    
    def __str__(self):
        return f"{self.test.nombre} - {self.get_tipo_display()}"

class PreguntaValores(models.Model):
    parte = models.ForeignKey(ParteTest, on_delete=models.CASCADE)
    texto = models.TextField()
    pagina = models.PositiveSmallIntegerField()
    
    def __str__(self):
        return f"Pregunta {self.id} - {self.texto[:50]}..."
    
class OpcionValores(models.Model):
    pregunta = models.ForeignKey(PreguntaValores, on_delete=models.CASCADE)
    letra = models.CharField(max_length=1)
    texto = models.CharField(max_length=300)
    columna = models.CharField(max_length=1)  # R, S, T, X, Y, Z
    
    def __str__(self):
        return f"Opción {self.letra} - {self.texto[:30]}"
    
class ResultadoValores(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    test = models.ForeignKey(TestValores, on_delete=models.CASCADE)
    fecha_completado = models.DateTimeField(auto_now_add=True)
    
    # Puntajes por valor
    teorico = models.FloatField(default=0)
    economico = models.FloatField(default=0)
    estetico = models.FloatField(default=0)
    social = models.FloatField(default=0)
    politico = models.FloatField(default=0)
    religioso = models.FloatField(default=0)
    
    # Percentiles
    teorico_percentil = models.FloatField(null=True, blank=True)
    economico_percentil = models.FloatField(null=True, blank=True)
    estetico_percentil = models.FloatField(null=True, blank=True)
    social_percentil = models.FloatField(null=True, blank=True)
    politico_percentil = models.FloatField(null=True, blank=True)
    religioso_percentil = models.FloatField(null=True, blank=True)

    clasificaciones = models.JSONField(default=dict)
    valor_dominante = models.CharField(max_length=50, default='')
    descripcion_dominante = models.TextField(default='')
    meta_dominante = models.CharField(max_length=255, default='')
    rangos_valores = models.JSONField(default=dict)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Resultado de {self.usuario} en {self.test.nombre}"
    
class TestDomino(models.Model):
    TIPO_DISPOSICION = [
        ('MATRIZ', 'Matriz rectangular'),
        ('ESPIRAL', 'Disposición en espiral'),
        ('FLOR', 'Disposición floral'),
    ]
    
    nombre = models.CharField(max_length=100, default="Test de Dominó D-48")
    descripcion = models.TextField(blank=True)
    tiempo_limite = models.PositiveIntegerField(default=25, help_text="Tiempo en minutos")
    instrucciones = models.TextField(blank=True)
    tipo_disposicion = models.CharField(
        max_length=10, 
        choices=TIPO_DISPOSICION, 
        default='MATRIZ',
        help_text="Tipo de disposición para los problemas"
    )
    
    def __str__(self):
        return self.nombre

class ProblemaDomino(models.Model):
    TIPO_PROBLEMA = [
        ('MATRIZ', 'Matriz rectangular'),
        ('ESPIRAL', 'Disposición en espiral'),
        ('FLOR', 'Disposición floral'),
    ]
    
    test = models.ForeignKey(TestDomino, on_delete=models.CASCADE, related_name='problemas')
    numero = models.PositiveIntegerField()
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_PROBLEMA, 
        default='MATRIZ',
        help_text="Tipo de disposición del problema"
    )
    
    matriz_filas = models.PositiveIntegerField(
        default=2, 
        null=True, 
        blank=True,
        help_text="Número de filas (solo para tipo matriz)"
    )
    matriz_columnas = models.PositiveIntegerField(
        default=3, 
        null=True, 
        blank=True,
        help_text="Número de columnas (solo para tipo matriz)"
    )
    
    fichas = models.JSONField()
    
    respuesta = models.JSONField()
    
    configuracion_extra = models.JSONField(
        null=True, 
        blank=True,
        help_text="Configuración adicional para disposiciones especiales"
    )
    
    class Meta:
        ordering = ['numero']
        unique_together = ['test', 'numero']
    
    def __str__(self):
        return f"Problema {self.numero} - Test Dominó"
    
    def get_fichas_display(self):
        """Método para visualizar mejor las fichas en el admin"""
        return json.dumps(self.fichas, indent=2)

class ResultadoDomino(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resultados_domino')
    test = models.ForeignKey(TestDomino, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    
    respuestas = models.JSONField()
    
    puntuacion = models.PositiveIntegerField(default=0)
    percentil = models.FloatField(null=True, blank=True)
    tiempo_utilizado = models.PositiveIntegerField(
        default=0, 
        help_text="Tiempo utilizado en segundos"
    )
    eficiencia = models.FloatField(default=0.0)  # Porcentaje de eficiencia
    diagnostico = models.CharField(max_length=50, default='')  # Capacidad intelectual
    baremo = models.JSONField(default=dict)  # Datos de baremación
    grupo_edad = models.CharField(max_length=20, default='general')

    def __str__(self):
        return f"Resultado de {self.usuario} - {self.puntuacion} pts"