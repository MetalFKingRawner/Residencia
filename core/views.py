from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from core.models import ConfiguracionPlataforma

def base_test(request):
    """Vista temporal para renderizar base.html sin contenido específico"""
    return render(request, 'base.html')

def user_login(request):
    # Capturamos el destino 'next'
    next_url = request.GET.get('next') or request.POST.get('next') or 'home'

    if 'course' in next_url or 'curso' in next_url:
        plantilla_base = 'courses/base_cursos.html' # o 'courses/base.html' dependiendo de cómo se llame tu archivo
    else:
        plantilla_base = 'base.html'

    # ── CANDADO DE SEGURIDAD ABSOLUTO ──
    #config, _ = ConfiguracionPlataforma.objects.get_or_create(id=1)
    
    #if not config.pruebas_activas:
        # Si las pruebas están cerradas, un usuario común NO tiene nada que hacer en el Login.
        # Solo procesamos el POST si el usuario que intenta loguearse resulta ser Staff (se valida abajo).
    #    if request.method == 'GET':
    #        messages.warning(request, "El acceso a la plataforma está deshabilitado por el momento. No hay evaluaciones activas.")
    #        return redirect('home')
    # ──────────────────────────────────



    # Si ya está autenticado, redirige inmediatamente
    if request.user.is_authenticated:
        return redirect(next_url)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # VALIDACIÓN EXTRA: Si las pruebas están cerradas, solo dejamos pasar a los Admins/Staff
            #if not config.pruebas_activas and not (user.is_staff or user.is_superuser):
            #    messages.error(request, "La plataforma está cerrada para estudiantes en este momento.")
            #    return redirect('home')
            config, _ = ConfiguracionPlataforma.objects.get_or_create(id=1)
            if not config.pruebas_activas and 'tests' in next_url:
                if not (user.is_staff or user.is_superuser):
                    messages.error(request, "La plataforma de pruebas está cerrada en este momento.")
                    return redirect('home')
                
            login(request, user)
            return redirect(next_url)
        else:
            return render(request, 'registration/login.html', {'error': 'Credenciales inválidas', 'next': next_url, 'base_template': plantilla_base})
    
    return render(request, 'registration/login.html', {'next': next_url, 'base_template': plantilla_base})

def prueba_requiere_login(request):
    return render(request, 'tests/prueba_requiere_login.html')