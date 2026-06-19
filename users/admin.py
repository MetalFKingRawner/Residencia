from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Campos a mostrar al CREAR un usuario
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 
                'email',
                'full_name',
                'password1', 
                'password2',
                'date_of_birth',
                'gender',
                'institution',
                'education_level',
                'occupation'
            ),
        }),
    )

    # Campos a mostrar al EDITAR un usuario
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {
            'fields': (
                'full_name',
                'email',
                'date_of_birth',
                'gender',
            )
        }),
        ('Información Adicional', {
            'fields': (
                'institution',
                'education_level',
                'occupation',
            )
        }),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    # Campos a mostrar en la lista de usuarios
    list_display = ('username', 'email', 'full_name', 'is_staff')
    
admin.site.register(CustomUser, CustomUserAdmin)