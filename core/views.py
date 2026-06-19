from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

def base_test(request):
    """Vista temporal para renderizar base.html sin contenido específico"""
    return render(request, 'base.html')

def user_login(request):
    # Si ya está autenticado, redirige inmediatamente
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or 'home'
            return redirect(next_url)
        else:
            return render(request, 'login.html', {'error': 'Credenciales inválidas'})
    
    # GET: Incluir parámetro next en el contexto
    return render(request, 'registration/login.html', {'next': request.GET.get('next', '')})

def prueba_requiere_login(request):
    return render(request, 'tests/prueba_requiere_login.html')