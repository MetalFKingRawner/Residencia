from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.urls import reverse_lazy

class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    def dispatch(self, request, *args, **kwargs):
        # 1. Atrapamos el parámetro ANTES de que Django limpie la URL por seguridad
        if 'next' in request.GET:
            request.session['reset_next'] = request.GET['next']
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        url = str(reverse_lazy('password_reset_complete'))
        # 2. Recuperamos el parámetro de la sesión para la última redirección
        next_url = self.request.session.get('reset_next') or ''
        if next_url:
            url += f"?next={next_url}"
        return url

urlpatterns = [
    # Registro
    path('registro/', views.signup, name='signup'),
    path(
        'logout/', 
        auth_views.LogoutView.as_view(next_page='home'), 
        name='logout'
    ),
    
    # Recuperación de contraseña
    path('password_reset/', views.password_reset_request, name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         CustomPasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), name='password_reset_complete'),

    # Nuevas rutas para dashboard y perfil
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/change-password/', views.change_password_ajax, name='change_password_ajax'),
    path('admin/user/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
]