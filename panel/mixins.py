# panel/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from courses.models import Curso  # Importamos desde la app courses

GRUPO_DIRECTIVO = 'Directivo / Coordinador'
GRUPO_INSTRUCTORES = 'Instructores'


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin estricto que verifica que el usuario sea staff (is_staff=True).
    Cubre al rol "Administrador del Sistema" (is_staff=True / is_superuser=True).
    """
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permisos para acceder a esta sección.")


class AdminOrStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Permite acceso a staff (Administrador del Sistema) o al grupo Directivo/Coordinador.
    Usado para gestión de usuarios, inscripciones y crear cursos.
    """
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()

    def handle_no_permission(self):
        raise PermissionDenied("Se requieren permisos de administrador para esta acción.")


class InstructorGroupRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Verifica que el usuario pertenezca al grupo "Instructores" o sea staff/Directivo.
    """
    def test_func(self):
        user = self.request.user
        es_admin = user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()
        return es_admin or user.groups.filter(name=GRUPO_INSTRUCTORES).exists()

    def handle_no_permission(self):
        raise PermissionDenied("Se requiere ser instructor o administrador para acceder a esta sección.")


class InstructorOrStaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Permite acceso total a staff/Directivo, o acceso restringido a instructores asignados al curso.
    """
    def test_func(self):
        user = self.request.user

        # 1. Staff (Administrador del Sistema) y Directivo/Coordinador tienen pase directo ("llave maestra")
        es_admin = user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()
        if es_admin:
            return True

        # 2. Verificar que pertenezca al grupo Instructores
        if not user.groups.filter(name=GRUPO_INSTRUCTORES).exists():
            return False

        # 3. Obtener el curso
        curso = self._get_curso()
        if not curso:
            # Si no hay un curso específico que validar (ej. en listados globales), permitimos pasar.
            # El get_queryset de la vista se encargará de filtrar lo que ven.
            return True

        # 4. Verificar que sea el instructor asignado a ESE curso
        return curso.instructor == user

    def _get_curso(self):
        """Obtiene el curso de los kwargs o del objeto."""
        if hasattr(self, 'get_curso'): return self.get_curso()
        if hasattr(self, 'curso'): return self.curso
        if hasattr(self, 'object'): return getattr(self.object, 'curso', None)
        curso_pk = self.kwargs.get('curso_pk')
        if curso_pk: return get_object_or_404(Curso, pk=curso_pk)
        return None

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permiso para gestionar este curso.")


class CursoPermissionMixin(InstructorOrStaffMixin):
    """
    Extiende InstructorOrStaffMixin para vistas que trabajan con un curso específico.
    Útil para vistas de Lecciones y Recursos.
    """
    def get_curso(self):
        """Obtiene el curso desde curso_pk o pk en los kwargs."""
        curso_pk = self.kwargs.get('curso_pk') or self.kwargs.get('pk')
        if curso_pk:
            return get_object_or_404(Curso, pk=curso_pk)

        if hasattr(self, 'object'):
            if hasattr(self.object, 'curso'):
                return self.object.curso
            if isinstance(self.object, Curso):
                return self.object

        return None

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class InstructorCanViewInscripcionesMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Permite a los instructores y administradores ver las inscripciones.
    """
    def test_func(self):
        user = self.request.user

        es_admin = user.is_staff or user.groups.filter(name=GRUPO_DIRECTIVO).exists()
        if es_admin:
            return True

        if not user.groups.filter(name=GRUPO_INSTRUCTORES).exists():
            return False

        return True

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permiso para ver inscripciones.")