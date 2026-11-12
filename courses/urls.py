from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.CursoListView.as_view(), name='curso_list'),        # /cursos/
    path('catalogo/', views.CursoCatalogoView.as_view(), name='curso_catalogo'),
    path('<slug:slug>/', views.CursoDetailView.as_view(), name='curso_detail'),
    path('<slug:slug>/leccion/<int:orden>/', views.LeccionDetailView.as_view(), name='leccion_detail'),
    path('<slug:slug>/leccion/<int:orden>/completar/', views.completar_leccion, name='completar_leccion'),
    path('<slug:slug>/solicitar/', views.solicitar_acceso, name='solicitar_acceso'),
    path('<slug:slug>/certificado/', views.descargar_certificado, name='descargar_certificado'),
]