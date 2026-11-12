# panel/management/commands/init_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from courses.models import Curso, Leccion, RecursoLeccion, Inscripcion
from users.models import CustomUser
from tests.models import ResultadoValores, ResultadoDomino


class Command(BaseCommand):
    help = 'Inicializa grupos y permisos para la plataforma'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Limpia los permisos de los grupos antes de reasignarlos (útil tras cambios)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\nIniciando creación de grupos y permisos...\n'))

        nombres_grupos = (
            'Administrador del Sistema',
            'Directivo / Coordinador',
            'Instructores',
            'Estudiantes',
        )

        if options['reset']:
            self.stdout.write(self.style.WARNING('⚠ Modo --reset: limpiando permisos de grupos existentes...\n'))
            for nombre in nombres_grupos:
                try:
                    grupo = Group.objects.get(name=nombre)
                    grupo.permissions.clear()
                    self.stdout.write(f'  • Permisos de "{nombre}" limpiados')
                except Group.DoesNotExist:
                    pass
            self.stdout.write('')

        # ----------------------------------------
        # 1. Crear grupos
        # ----------------------------------------
        self.stdout.write(self.style.HTTP_INFO('[ Grupos ]'))

        grupo_sistema, created = Group.objects.get_or_create(name='Administrador del Sistema')
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Administrador del Sistema" {"creado" if created else "ya existe"}'
        ))

        grupo_directivo, created = Group.objects.get_or_create(name='Directivo / Coordinador')
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Directivo / Coordinador" {"creado" if created else "ya existe"}'
        ))

        grupo_instructores, created = Group.objects.get_or_create(name='Instructores')
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Instructores" {"creado" if created else "ya existe"}'
        ))

        grupo_estudiantes, created = Group.objects.get_or_create(name='Estudiantes')
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Estudiantes" {"creado" if created else "ya existe"}'
        ))

        # ----------------------------------------
        # 2. Obtener ContentTypes
        # ----------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('[ ContentTypes ]'))

        try:
            curso_ct           = ContentType.objects.get_for_model(Curso)
            leccion_ct         = ContentType.objects.get_for_model(Leccion)
            recurso_ct         = ContentType.objects.get_for_model(RecursoLeccion)
            inscripcion_ct     = ContentType.objects.get_for_model(Inscripcion)
            customuser_ct      = ContentType.objects.get_for_model(CustomUser)
            resultadovalores_ct = ContentType.objects.get_for_model(ResultadoValores)
            resultadodomino_ct  = ContentType.objects.get_for_model(ResultadoDomino)
            self.stdout.write(self.style.SUCCESS('  ✓ ContentTypes obtenidos correctamente'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error al obtener ContentTypes: {e}'))
            self.stdout.write(self.style.ERROR('  Asegúrate de haber ejecutado migrate antes de este command.'))
            return

        # ----------------------------------------
        # 3. Permisos auto-generados por Django
        #    (add, change, delete, view por modelo)
        # ----------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('[ Permisos estándar de Django ]'))

        def get_perm(codename, content_type):
            """Obtiene un permiso estándar generado por Django."""
            try:
                perm = Permission.objects.get(codename=codename, content_type=content_type)
                self.stdout.write(f'  ✓ {codename}')
                return perm
            except Permission.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Permiso "{codename}" no encontrado. '
                    f'¿Ejecutaste migrate?'
                ))
                return None

        # Permisos sobre Curso (declarados en Meta del modelo, Django los crea al migrar)
        perm_ver_todos_cursos      = get_perm('puede_ver_todos_cursos', curso_ct)
        perm_asignar_instructores  = get_perm('puede_asignar_instructores', curso_ct)

        # Permisos CRUD estándar sobre Lección
        perm_add_leccion    = get_perm('add_leccion', leccion_ct)
        perm_change_leccion = get_perm('change_leccion', leccion_ct)
        perm_delete_leccion = get_perm('delete_leccion', leccion_ct)
        perm_view_leccion   = get_perm('view_leccion', leccion_ct)

        # Permisos CRUD estándar sobre RecursoLeccion
        perm_add_recurso    = get_perm('add_recursoleccion', recurso_ct)
        perm_change_recurso = get_perm('change_recursoleccion', recurso_ct)
        perm_delete_recurso = get_perm('delete_recursoleccion', recurso_ct)
        perm_view_recurso   = get_perm('view_recursoleccion', recurso_ct)

        # Permisos sobre Inscripcion (Directivo puede gestionar inscripciones completas)
        perm_add_inscripcion    = get_perm('add_inscripcion', inscripcion_ct)
        perm_change_inscripcion = get_perm('change_inscripcion', inscripcion_ct)
        perm_delete_inscripcion = get_perm('delete_inscripcion', inscripcion_ct)
        perm_view_inscripcion   = get_perm('view_inscripcion', inscripcion_ct)

        # Permisos CRUD estándar sobre CustomUser (gestión de usuarios)
        perm_add_user    = get_perm('add_customuser', customuser_ct)
        perm_change_user = get_perm('change_customuser', customuser_ct)
        perm_delete_user = get_perm('delete_customuser', customuser_ct)
        perm_view_user    = get_perm('view_customuser', customuser_ct)

        # Permisos de solo lectura sobre resultados de pruebas psicométricas
        perm_view_resultado_valores = get_perm('view_resultadovalores', resultadovalores_ct)
        perm_view_resultado_domino  = get_perm('view_resultadodomino', resultadodomino_ct)

        # ----------------------------------------
        # 4. Permisos personalizados del command
        #    (los que NO están en ningún Meta)
        # ----------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('[ Permisos personalizados ]'))

        def get_or_create_perm(codename, name, content_type):
            """Crea un permiso personalizado si no existe, o lo obtiene si ya existe."""
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name},
            )
            estado = 'creado' if created else 'ya existe'
            self.stdout.write(self.style.SUCCESS(f'  ✓ {codename} ({estado})'))
            return perm

        perm_ver_avance = get_or_create_perm(
            codename='puede_ver_avance_estudiantes',
            name='Puede ver el avance de estudiantes en sus cursos',
            content_type=curso_ct,
        )

        # ----------------------------------------
        # 5. Asignar permisos a cada grupo
        # ----------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('[ Asignación de permisos ]'))

        # Administrador del Sistema: soporte técnico / mantenimiento.
        # No se le asignan permisos de modelo de negocio aquí a propósito:
        # el acceso real de este rol se controla vía is_superuser=True
        # (que ya otorga acceso total al admin de Django, sin necesidad
        # de permisos de grupo explícitos). El grupo existe únicamente
        # como etiqueta para tus mixins/context_processors del panel.
        grupo_sistema.permissions.set([])
        self.stdout.write(self.style.SUCCESS(
            '  ✓ "Administrador del Sistema": 0 permisos asignados '
            '(el acceso se controla con is_superuser=True en el usuario)'
        ))

        # Directivo / Coordinador: privilegios operativos completos,
        # pero SIN llegar al nivel de superusuario.
        perms_directivo = [
            perm_ver_todos_cursos,
            perm_asignar_instructores,
            perm_add_leccion, perm_change_leccion, perm_delete_leccion, perm_view_leccion,
            perm_add_recurso, perm_change_recurso, perm_delete_recurso, perm_view_recurso,
            perm_add_inscripcion, perm_change_inscripcion, perm_delete_inscripcion, perm_view_inscripcion,
            perm_add_user, perm_change_user, perm_delete_user, perm_view_user,
            perm_view_resultado_valores, perm_view_resultado_domino,
            perm_ver_avance,
        ]
        perms_directivo = [p for p in perms_directivo if p is not None]
        grupo_directivo.permissions.set(perms_directivo)
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Directivo / Coordinador": {len(perms_directivo)} permisos asignados'
        ))

        # Instructores: gestión de contenido de sus cursos y avance de estudiantes
        # Nota: el filtrado de "solo sus cursos" se maneja en la lógica de las views,
        # no en los permisos. Estos permisos solo abren la puerta.
        perms_instructor = [
            perm_add_leccion, perm_change_leccion, perm_delete_leccion, perm_view_leccion,
            perm_add_recurso, perm_change_recurso, perm_delete_recurso, perm_view_recurso,
            perm_view_inscripcion,
            perm_ver_avance,
        ]
        perms_instructor = [p for p in perms_instructor if p is not None]
        grupo_instructores.permissions.set(perms_instructor)
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Instructores": {len(perms_instructor)} permisos asignados'
        ))

        # Estudiantes: solo lectura de cursos en los que están inscritos
        # Nota: el acceso real se controla por la lógica de Inscripcion en las views.
        perms_estudiante = [
            perm_view_leccion,
            perm_view_recurso,
        ]
        perms_estudiante = [p for p in perms_estudiante if p is not None]
        grupo_estudiantes.permissions.set(perms_estudiante)
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ "Estudiantes": {len(perms_estudiante)} permisos asignados'
        ))

        # ----------------------------------------
        # 6. Resumen final
        # ----------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('¡Inicialización completada exitosamente!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write('Resumen de grupos:')
        for grupo in (grupo_sistema, grupo_directivo, grupo_instructores, grupo_estudiantes):
            self.stdout.write(
                f'  • {grupo.name}: '
                f'{grupo.user_set.count()} usuarios | '
                f'{grupo.permissions.count()} permisos'
            )
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            'Recuerda: los permisos de grupo se cachean por sesión.\n'
            'Si asignaste un usuario a un grupo con sesión activa,\n'
            'cierra sesión y vuelve a entrar para que los permisos surtan efecto.\n'
        ))