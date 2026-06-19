from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('landing.urls')),
    path('usuarios/', include('users.urls')),  # Incluye las URLs de users (logout aquí)
    path('', include('core.urls')),  # Incluye las URLs de core
    path('tests/', include('tests.urls')),
    path('cursos/', include('courses.urls')),
    #path('usuarios/', include('users.urls')),  # URLs de autenticación
    #path('login/', include('core.urls')),  # Solo una ruta para login
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)