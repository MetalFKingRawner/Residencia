from django.urls import path
from . import views
from core.views import prueba_requiere_login
from django.contrib.auth.decorators import login_required

app_name = 'tests'

urlpatterns = [
    path('', views.test_index, name='index'),
    path('valores/', views.inicio_test_valores, name='inicio_test_valores'),
    path('valores/segunda', views.inicio_segundo_test_valores, name='inicio_segundo_test_valores'),
    path('valores/primera-parte/', views.primera_parte_valores, name='primera_parte_valores'),  # ← USADO EN FORM
    path('valores/segunda-parte/', views.segunda_parte_valores, name='segunda_parte_valores'),  # ← USADO EN FORM
    path('calcular-resultados-valores/', views.calcular_resultados_valores, name='calcular_resultados_valores'),
    path('resultados-valores/', views.mostrar_resultados_valores, name='mostrar_resultados_valores'),
    path('reporte-valores/<int:resultado_id>/', views.generar_pdf_valores, name='reporte_valores'),
    # URLs para el Test de Dominó
    path('domino/', views.inicio_domino, name='inicio_domino'),
    path('domino/test/', views.test_domino, name='test_domino'),
    path('domino/ejercicio/<int:problema_id>/', views.detalle_problema_domino, name='detalle_problema_domino'),
    path('test-simple/', views.test_index, name='test_simple'),
    path('domino/calcular-resultados/', views.calcular_resultados_domino, name='calcular_resultados_domino'),
    path('domino/resultados/<int:resultado_id>/', views.resultados_domino, name='resultados_domino'),
    path('resultados/domino/<int:resultado_id>/pdf/', views.generar_pdf_domino, name='reporte_domino'),
    path('requiere-login/', prueba_requiere_login, name='prueba_requiere_login'),
    path('health/', views.health_check, name='health_check'),  # <--- nuevo
]