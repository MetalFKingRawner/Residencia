from .models import ConfiguracionPlataforma

def config_global(request):
    """
    Inyecta la configuración de la plataforma en todos los templates.
    Si no existe ninguna configuración en la base de datos, la crea apagada por defecto.
    """
    config, created = ConfiguracionPlataforma.objects.get_or_create(id=1)
    
    return {
        'CONFIG': config
    }

# core/context_processors.py
def plantilla_base_dinamica(request):
    # Añadimos la sesión (request.session.get) a la lista de búsqueda
    next_url = request.GET.get('next') or request.POST.get('next') or request.session.get('reset_next') or request.path

    if not next_url:
        next_url = request.get_full_path()
    
    # IMPORTANTE: Asegúrate de que la ruta sea la correcta de tu archivo (courses/base_cursos.html o base_cursos.html)
    if 'course' in next_url or 'curso' in next_url:
        base_template = 'courses/base_cursos.html' 
    else:
        base_template = 'base.html'
        
    return {
        'base_template': base_template
    }