from django.contrib.auth import login
from django.contrib.auth.forms import PasswordResetForm
from django.shortcuts import render, redirect

from users.models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm
from django.contrib.auth.decorators import login_required
from tests.models import ResultadoValores, ResultadoDomino, TestValores, TestDomino
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                email_template_name='registration/password_reset_email.html',
                subject_template_name='registration/password_reset_subject.txt',
                from_email="no-reply@CentroDHAE.com",
                request=request
            )
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()
    return render(request, 'registration/password_reset.html', {'form': form})

@login_required
def dashboard(request):
    # Verificar si el usuario es staff/admin
    if request.user.is_staff or request.user.is_superuser:
        return admin_dashboard(request)
    
    # Lógica original para usuarios normales
    return user_dashboard(request)

def user_dashboard(request):
    """Dashboard para usuarios normales"""
    resultados_valores = ResultadoValores.objects.filter(usuario=request.user)
    resultados_domino = ResultadoDomino.objects.filter(usuario=request.user)
    
    total_valores = resultados_valores.count()
    total_domino = resultados_domino.count()
    total_tests = total_valores + total_domino
    
    ultimas_valores = list(resultados_valores.order_by('-fecha_completado')[:3])
    ultimas_domino = list(resultados_domino.order_by('-fecha')[:3])
    ultimas_pruebas = ultimas_valores + ultimas_domino
    
    ultimas_pruebas = sorted(
        ultimas_pruebas,
        key=lambda x: x.fecha if hasattr(x, 'fecha') else x.fecha_completado,
        reverse=True
    )[:5]
    
    avg_valores = resultados_valores.aggregate(
        teorico=Avg('teorico'),
        economico=Avg('economico'),
        estetico=Avg('estetico'),
        social=Avg('social'),
        politico=Avg('politico'),
        religioso=Avg('religioso')
    )
    
    context = {
        'user': request.user,
        'ultimas_pruebas': ultimas_pruebas,
        'total_tests': total_tests,
        'total_valores': total_valores,
        'total_domino': total_domino,
        'avg_valores': avg_valores,
    }
    return render(request, 'users/dashboard.html', context)

def admin_dashboard(request):
    """Dashboard para administradores"""
    # Obtener todos los usuarios
    usuarios = CustomUser.objects.all().order_by('-date_joined')
    
    # Obtener parámetros de filtro
    search_query = request.GET.get('search', '')
    institution_filter = request.GET.get('institution', '')
    test_type_filter = request.GET.get('test_type', '')
    date_range = request.GET.get('date_range', 'all')
    
    # Aplicar filtros
    if search_query:
        usuarios = usuarios.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if institution_filter:
        usuarios = usuarios.filter(institution__icontains=institution_filter)
    
    # Filtrar por rango de fechas
    if date_range != 'all':
        today = timezone.now().date()
        if date_range == 'today':
            usuarios = usuarios.filter(date_joined__date=today)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            usuarios = usuarios.filter(date_joined__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            usuarios = usuarios.filter(date_joined__date__gte=month_ago)
    
    # Paginación
    paginator = Paginator(usuarios, 20)  # 20 usuarios por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener estadísticas generales
    total_usuarios = CustomUser.objects.count()
    total_tests_valores = ResultadoValores.objects.count()
    total_tests_domino = ResultadoDomino.objects.count()
    
    # Obtener instituciones únicas para el filtro
    instituciones = CustomUser.objects.exclude(
        institution__isnull=True
    ).exclude(
        institution=''
    ).values_list('institution', flat=True).distinct()
    
    # Para cada usuario en la página, obtener sus pruebas
    usuarios_con_pruebas = []
    for usuario in page_obj:
        pruebas_valores = ResultadoValores.objects.filter(usuario=usuario).count()
        pruebas_domino = ResultadoDomino.objects.filter(usuario=usuario).count()
        
        usuarios_con_pruebas.append({
            'usuario': usuario,
            'pruebas_valores': pruebas_valores,
            'pruebas_domino': pruebas_domino,
            'total_pruebas': pruebas_valores + pruebas_domino,
            'ultima_prueba': get_ultima_prueba(usuario)
        })
    
    context = {
        'usuarios_con_pruebas': usuarios_con_pruebas,
        'page_obj': page_obj,
        'total_usuarios': total_usuarios,
        'total_tests_valores': total_tests_valores,
        'total_tests_domino': total_tests_domino,
        'instituciones': instituciones,
        'filtros': {
            'search': search_query,
            'institution': institution_filter,
            'test_type': test_type_filter,
            'date_range': date_range,
        }
    }
    return render(request, 'users/admin_dashboard.html', context)

def get_ultima_prueba(usuario):
    """Obtiene la fecha de la última prueba realizada por un usuario"""
    ultimo_valor = ResultadoValores.objects.filter(
        usuario=usuario
    ).order_by('-fecha_completado').first()
    
    ultimo_domino = ResultadoDomino.objects.filter(
        usuario=usuario
    ).order_by('-fecha').first()
    
    if ultimo_valor and ultimo_domino:
        if ultimo_valor.fecha_completado > ultimo_domino.fecha:
            return ultimo_valor.fecha_completado
        return ultimo_domino.fecha
    elif ultimo_valor:
        return ultimo_valor.fecha_completado
    elif ultimo_domino:
        return ultimo_domino.fecha
    
    return None

@login_required
def profile_view(request):
    user = request.user
    # Obtener historial completo de pruebas
    resultados_valores = ResultadoValores.objects.filter(usuario=user).order_by('-fecha_completado')
    resultados_domino = ResultadoDomino.objects.filter(usuario=user).order_by('-fecha')
    
    return render(request, 'users/profile.html', {
        'user': user,
        'resultados_valores': resultados_valores,
        'resultados_domino': resultados_domino
    })

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'users/update_profile.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        # Redirigir a la URL solicitada originalmente o al dashboard
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return super().get_success_url()
    
@login_required
def admin_user_detail(request, user_id):
    """Vista detallada de un usuario específico para administradores"""
    # Verificar que el usuario actual es admin
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('dashboard')
    
    # Obtener el usuario especificado
    usuario = get_object_or_404(CustomUser, id=user_id)
    
    # Obtener todas las pruebas del usuario
    resultados_valores = ResultadoValores.objects.filter(
        usuario=usuario
    ).order_by('-fecha_completado')
    
    resultados_domino = ResultadoDomino.objects.filter(
        usuario=usuario
    ).order_by('-fecha')
    
    # Estadísticas generales del usuario
    total_valores = resultados_valores.count()
    total_domino = resultados_domino.count()
    total_pruebas = total_valores + total_domino
    
    # Calcular promedios de valores
    avg_valores = resultados_valores.aggregate(
        teorico=Avg('teorico'),
        economico=Avg('economico'),
        estetico=Avg('estetico'),
        social=Avg('social'),
        politico=Avg('politico'),
        religioso=Avg('religioso')
    )
    
    # Calcular promedio de dominó
    avg_domino = resultados_domino.aggregate(
        puntuacion=Avg('puntuacion'),
        percentil=Avg('percentil'),
        eficiencia=Avg('eficiencia')
    )
    
    # Obtener la distribución de valores dominantes
    valores_dominantes = resultados_valores.values('valor_dominante').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Obtener diagnósticos más comunes de dominó
    diagnosticos = resultados_domino.values('diagnostico').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Preparar datos para gráficos (si decides añadirlos después)
    datos_grafico_valores = []
    if avg_valores['teorico']:
        datos_grafico_valores = [
            {'valor': 'Teórico', 'puntaje': avg_valores['teorico'] or 0},
            {'valor': 'Económico', 'puntaje': avg_valores['economico'] or 0},
            {'valor': 'Estético', 'puntaje': avg_valores['estetico'] or 0},
            {'valor': 'Social', 'puntaje': avg_valores['social'] or 0},
            {'valor': 'Político', 'puntaje': avg_valores['politico'] or 0},
            {'valor': 'Religioso', 'puntaje': avg_valores['religioso'] or 0},
        ]
    
    context = {
        'usuario': usuario,
        'resultados_valores': resultados_valores,
        'resultados_domino': resultados_domino,
        'total_valores': total_valores,
        'total_domino': total_domino,
        'total_pruebas': total_pruebas,
        'avg_valores': avg_valores,
        'avg_domino': avg_domino,
        'valores_dominantes': valores_dominantes,
        'diagnosticos': diagnosticos,
        'datos_grafico_valores': datos_grafico_valores,
    }
    
    return render(request, 'users/admin_user_detail.html', context)