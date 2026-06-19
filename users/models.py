from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    first_name = None
    last_name = None

    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
        ('N', 'Prefiero no decir'),
    ]

    full_name = models.CharField("Nombre completo", max_length=255)
    date_of_birth = models.DateField("Fecha de nacimiento", null=True, blank=True)
    gender = models.CharField(
        "Género",
        max_length=1,
        choices=GENDER_CHOICES,
        default='N'
    )
    institution = models.CharField(
        "Institución (Escuela/Empresa)",
        max_length=255,
        blank=True,
        null=True
    )
    education_level = models.CharField(
        "Nivel de estudios",
        max_length=255,
        blank=True,
        null=True
    )
    occupation = models.CharField(
        "Ocupación",
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.full_name
    