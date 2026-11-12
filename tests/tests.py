# tests/tests.py
# Ejecutar con:  python manage.py test tests.tests -v 2
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.views import View

from core.models import ConfiguracionPlataforma
from panel.mixins import (
    GRUPO_DIRECTIVO,
    GRUPO_INSTRUCTORES,
    AdminOrStaffRequiredMixin,
    InstructorCanViewInscripcionesMixin,
    InstructorGroupRequiredMixin,
    StaffRequiredMixin,
)
from tests.models import (
    ParteTest,
    ProblemaDomino,
    ResultadoDomino,
    ResultadoValores,
    TestDomino,
    TestValores,
)
from tests.views import procesar_pregunta_segunda_parte

User = get_user_model()
PASSWORD = 'Prueba12345!'
NOMBRE_TEST_DOMINO = 'Test de Dominó D-48'

# En producción DEBUG=False activa SECURE_SSL_REDIRECT; el cliente de pruebas usa
# http, así que lo desactivamos aquí. Los estáticos con manifest (WhiteNoise)
# tampoco existen en el entorno de pruebas, por eso se usa el almacenamiento simple.
AJUSTES_PRUEBA = dict(
    SECURE_SSL_REDIRECT=False,
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
)


def crear_usuario(username, **extra):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        full_name=username.capitalize(),
        **extra,
    )


class UsuariosBase(TestCase):
    """Crea un usuario por cada rol de la plataforma."""

    @classmethod
    def setUpTestData(cls):
        # Los grupos los crea el comando init_groups; la BD de pruebas empieza vacía.
        g_directivo, _ = Group.objects.get_or_create(name=GRUPO_DIRECTIVO)
        g_instructores, _ = Group.objects.get_or_create(name=GRUPO_INSTRUCTORES)

        cls.alumno = crear_usuario('alumno')
        cls.otro_alumno = crear_usuario('otroalumno')
        cls.staff = crear_usuario('staff', is_staff=True)
        cls.directivo = crear_usuario('directivo')
        cls.directivo.groups.add(g_directivo)
        cls.instructor = crear_usuario('instructor')
        cls.instructor.groups.add(g_instructores)


# ---------------------------------------------------------------------------
# 1. Permisos de los mixins (panel/mixins.py)
# ---------------------------------------------------------------------------
class PermisosMixinsTests(UsuariosBase):
    def setUp(self):
        self.factory = RequestFactory()

    def _pedir(self, mixin, usuario):
        class Vista(mixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse('ok')

        request = self.factory.get('/')
        request.user = usuario
        return Vista.as_view()(request)

    def assertPermite(self, mixin, usuario):
        self.assertEqual(self._pedir(mixin, usuario).status_code, 200)

    def assertNiega(self, mixin, usuario):
        with self.assertRaises(PermissionDenied):
            self._pedir(mixin, usuario)

    # StaffRequiredMixin: solo is_staff
    def test_staff_mixin_permite_solo_staff(self):
        self.assertPermite(StaffRequiredMixin, self.staff)
        self.assertNiega(StaffRequiredMixin, self.directivo)
        self.assertNiega(StaffRequiredMixin, self.instructor)
        self.assertNiega(StaffRequiredMixin, self.alumno)

    # AdminOrStaffRequiredMixin: staff o Directivo/Coordinador
    def test_admin_mixin_permite_staff_y_directivo(self):
        self.assertPermite(AdminOrStaffRequiredMixin, self.staff)
        self.assertPermite(AdminOrStaffRequiredMixin, self.directivo)

    def test_admin_mixin_niega_instructor_alumno_y_anonimo(self):
        self.assertNiega(AdminOrStaffRequiredMixin, self.instructor)
        self.assertNiega(AdminOrStaffRequiredMixin, self.alumno)
        self.assertNiega(AdminOrStaffRequiredMixin, AnonymousUser())

    # InstructorGroupRequiredMixin: instructor, directivo o staff
    def test_instructor_group_mixin(self):
        for usuario in (self.instructor, self.directivo, self.staff):
            self.assertPermite(InstructorGroupRequiredMixin, usuario)
        self.assertNiega(InstructorGroupRequiredMixin, self.alumno)
        self.assertNiega(InstructorGroupRequiredMixin, AnonymousUser())

    # InstructorCanViewInscripcionesMixin
    def test_ver_inscripciones_mixin(self):
        for usuario in (self.instructor, self.directivo, self.staff):
            self.assertPermite(InstructorCanViewInscripcionesMixin, usuario)
        self.assertNiega(InstructorCanViewInscripcionesMixin, self.alumno)


# ---------------------------------------------------------------------------
# 2. Acceso a resultados del test de Dominó (privacidad de los datos)
# ---------------------------------------------------------------------------
@override_settings(**AJUSTES_PRUEBA)
class AccesoResultadosDominoTests(UsuariosBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        test, _ = TestDomino.objects.get_or_create(nombre=NOMBRE_TEST_DOMINO)
        cls.resultado = ResultadoDomino.objects.create(
            usuario=cls.alumno,
            test=test,
            respuestas={},
            puntuacion=30,
            percentil=50,
            eficiencia=80.0,
            diagnostico='Término medio',
            grupo_edad='18-30',
        )

    RESPUESTAS_DE_BLOQUEO = (302, 403, 404)

    def test_dueno_puede_ver_su_resultado(self):
        self.client.force_login(self.alumno)
        r = self.client.get(reverse('tests:resultados_domino', args=[self.resultado.id]))
        self.assertEqual(r.status_code, 200)

    def test_dueno_puede_descargar_su_pdf(self):
        self.client.force_login(self.alumno)
        r = self.client.get(reverse('tests:reporte_domino', args=[self.resultado.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_staff_y_directivo_pueden_ver_resultado_ajeno(self):
        # Decisión de diseño: el personal (staff / Directivo) puede consultar resultados.
        url = reverse('tests:resultados_domino', args=[self.resultado.id])
        for usuario in (self.staff, self.directivo):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_otro_usuario_no_debe_ver_resultado_ajeno(self):
        self.client.force_login(self.otro_alumno)
        r = self.client.get(reverse('tests:resultados_domino', args=[self.resultado.id]))
        self.assertIn(r.status_code, self.RESPUESTAS_DE_BLOQUEO,
                      'Un usuario puede ver el resultado de otra persona')

    def test_otro_usuario_no_debe_descargar_pdf_ajeno(self):
        self.client.force_login(self.otro_alumno)
        r = self.client.get(reverse('tests:reporte_domino', args=[self.resultado.id]))
        self.assertIn(r.status_code, self.RESPUESTAS_DE_BLOQUEO,
                      'Un usuario puede descargar el PDF de otra persona')

    def test_anonimo_no_debe_ver_resultado(self):
        r = self.client.get(reverse('tests:resultados_domino', args=[self.resultado.id]))
        self.assertIn(r.status_code, self.RESPUESTAS_DE_BLOQUEO,
                      'Un visitante sin sesión puede ver un resultado')

    def test_anonimo_no_debe_descargar_pdf(self):
        r = self.client.get(reverse('tests:reporte_domino', args=[self.resultado.id]))
        self.assertIn(r.status_code, self.RESPUESTAS_DE_BLOQUEO,
                      'Un visitante sin sesión puede descargar un PDF')

    def test_enviar_domino_sin_sesion_redirige_al_login(self):
        # Con raise_request_exception=False un error interno se ve como 500
        # en lugar de romper la prueba con una excepción.
        self.client.raise_request_exception = False
        r = self.client.post(reverse('tests:calcular_resultados_domino'), {})
        self.assertEqual(r.status_code, 302,
                         'Enviar el test sin sesión no redirige (error interno)')


# ---------------------------------------------------------------------------
# 3. Cálculo del Dominó D-48: puntuación, percentil, diagnóstico
# ---------------------------------------------------------------------------
@override_settings(**AJUSTES_PRUEBA)
class CalculoDominoTests(TestCase):
    TOTAL_PROBLEMAS = 30

    @classmethod
    def setUpTestData(cls):
        cls.test_domino, _ = TestDomino.objects.get_or_create(nombre=NOMBRE_TEST_DOMINO)
        # Fecha de nacimiento fija dentro del grupo de 18 a 30 años
        nacimiento = date(date.today().year - 25, 1, 1)
        cls.usuario = crear_usuario('candidato', date_of_birth=nacimiento)
        cls.problemas = [
            ProblemaDomino.objects.create(
                test=cls.test_domino, numero=n, tipo='MATRIZ',
                fichas=[], respuesta=[1, 2],
            )
            for n in range(1, cls.TOTAL_PROBLEMAS + 1)
        ]

    def _enviar(self, correctas, incorrectas):
        """Contesta bien las primeras N, mal las siguientes y deja el resto en blanco."""
        datos = {}
        for i, problema in enumerate(self.problemas):
            if i < correctas:
                sup, inf = '1', '2'
            elif i < correctas + incorrectas:
                sup, inf = '9', '9'
            else:
                continue
            datos[f'problema_{problema.id}_superior'] = sup
            datos[f'problema_{problema.id}_inferior'] = inf
        self.client.force_login(self.usuario)
        self.client.post(reverse('tests:calcular_resultados_domino'), datos)
        return ResultadoDomino.objects.filter(usuario=self.usuario).latest('id')

    def test_todas_correctas_grupo_18_30(self):
        resultado = self._enviar(correctas=30, incorrectas=0)
        self.assertEqual(resultado.grupo_edad, '18-30')
        self.assertEqual(resultado.puntuacion, 30)
        self.assertEqual(resultado.percentil, 40)  # 30 >= 29 en el baremo 18-30
        self.assertEqual(resultado.eficiencia, 100.0)
        self.assertEqual(resultado.diagnostico, 'Inferior al término medio')

    def test_con_errores_y_omitidas(self):
        # 20 correctas, 5 incorrectas y 5 en blanco: intentadas = 25
        resultado = self._enviar(correctas=20, incorrectas=5)
        self.assertEqual(resultado.puntuacion, 20)
        self.assertEqual(resultado.eficiencia, 80.0)  # 20 / 25
        self.assertEqual(resultado.percentil, 10)     # 20 >= 20 en el baremo 18-30
        self.assertEqual(resultado.diagnostico, 'Deficiente')

    def test_sin_respuestas_da_cero(self):
        resultado = self._enviar(correctas=0, incorrectas=0)
        self.assertEqual(resultado.puntuacion, 0)
        self.assertEqual(resultado.eficiencia, 0)
        self.assertEqual(resultado.percentil, 0)
        self.assertEqual(resultado.diagnostico, 'Deficiente')


# ---------------------------------------------------------------------------
# 4. Test de Allport: suma de la segunda parte (sin base de datos)
# ---------------------------------------------------------------------------
class ProcesarPreguntaAllportTests(SimpleTestCase):
    PREGUNTA = {
        'id': 10,
        'columnas_opciones': [
            {'letra': 'a', 'columna': 'R'},
            {'letra': 'b', 'columna': 'S'},
        ],
    }

    def _totales(self):
        return {c: 0.0 for c in 'RSTXYZ'}

    def test_suma_los_puntos_en_la_columna_de_cada_opcion(self):
        totales = self._totales()
        respuestas = {'puntos_p10_a': 2, 'puntos_p10_b': 1}
        procesar_pregunta_segunda_parte(self.PREGUNTA, respuestas, totales)
        self.assertEqual(totales['R'], 2.0)
        self.assertEqual(totales['S'], 1.0)

    def test_pregunta_omitida_reparte_2_5_por_opcion(self):
        totales = self._totales()
        procesar_pregunta_segunda_parte(self.PREGUNTA, {}, totales)
        self.assertEqual(totales['R'], 2.5)
        self.assertEqual(totales['S'], 2.5)

    def test_valor_no_numerico_cuenta_como_cero(self):
        totales = self._totales()
        respuestas = {'puntos_p10_a': 'abc', 'puntos_p10_b': 3}
        procesar_pregunta_segunda_parte(self.PREGUNTA, respuestas, totales)
        self.assertEqual(totales['R'], 0.0)
        self.assertEqual(totales['S'], 3.0)


# ---------------------------------------------------------------------------
# 5. Acceso al PDF del test de Allport (privacidad de los datos)
# ---------------------------------------------------------------------------
@override_settings(**AJUSTES_PRUEBA)
class AccesoResultadosValoresTests(UsuariosBase):
    RESPUESTAS_DE_BLOQUEO = (302, 403, 404)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        test = TestValores.objects.create(nombre='Test de Valores de Allport', autor='Allport')
        # Datos completos, como los que guarda calcular_resultados_valores:
        # la plantilla del PDF necesita clasificaciones (con color) y rangos.
        valores = ['Teórico', 'Económico', 'Estético', 'Social', 'Político', 'Religioso']
        clasificaciones = {
            v: {
                'clasificacion': 'NORMAL',
                'color': '#2a4d6e',
                'significado': 'Dentro del rango esperado para la población',
            }
            for v in valores
        }
        rangos_valores = {
            'Teórico': {'muy_bajo': 30, 'bajo': 34, 'alto': 45, 'muy_alto': 50},
            'Económico': {'muy_bajo': 28, 'bajo': 35, 'alto': 45, 'muy_alto': 51},
            'Estético': {'muy_bajo': 30, 'bajo': 35, 'alto': 46, 'muy_alto': 52},
            'Social': {'muy_bajo': 29, 'bajo': 34, 'alto': 44, 'muy_alto': 49},
            'Político': {'muy_bajo': 31, 'bajo': 35, 'alto': 48, 'muy_alto': 50},
            'Religioso': {'muy_bajo': 26, 'bajo': 33, 'alto': 48, 'muy_alto': 57},
        }
        cls.resultado = ResultadoValores.objects.create(
            usuario=cls.alumno, test=test,
            teorico=40, economico=40, estetico=40, social=40, politico=40, religioso=40,
            clasificaciones=clasificaciones,
            rangos_valores=rangos_valores,
            valor_dominante='Teórico',
            descripcion_dominante='Descripción de prueba',
            meta_dominante='Meta de prueba',
        )
        cls.url = reverse('tests:reporte_valores', args=[cls.resultado.id])

    def test_dueno_puede_descargar_su_pdf(self):
        self.client.force_login(self.alumno)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_otro_usuario_no_debe_descargar_pdf_ajeno(self):
        self.client.force_login(self.otro_alumno)
        r = self.client.get(self.url)
        self.assertIn(r.status_code, self.RESPUESTAS_DE_BLOQUEO,
                      'Un usuario puede descargar el PDF de valores de otra persona')

    def test_anonimo_no_debe_descargar_pdf(self):
        r = self.client.get(self.url)
        self.assertIn(r.status_code, self.RESPUESTAS_DE_BLOQUEO,
                      'Un visitante sin sesión puede descargar un PDF de valores')


# ---------------------------------------------------------------------------
# 6. Interruptor pruebas_activas (core.ConfiguracionPlataforma)
# ---------------------------------------------------------------------------
@override_settings(**AJUSTES_PRUEBA)
class InterruptorPruebasActivasTests(UsuariosBase):
    # inicio_domino/inicio_test_valores son páginas de presentación: siempre
    # cargan (200), pero ocultan el botón de inicio y muestran un aviso cuando
    # las pruebas están cerradas. Solo test_domino, que sí inicia el test, se
    # bloquea a nivel de URL.
    # Cada página de presentación tiene su propio texto de botón cuando está abierta.
    PAGINAS_DE_PRESENTACION = {
        'tests:inicio_domino': 'Comenzar la Evaluación',
        'tests:inicio_test_valores': 'Comenzar Primera Parte',
    }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # inicio_domino / inicio_test_valores buscan estos registros por nombre;
        # sin ellos la vista da 500 en lugar de reflejar el estado del interruptor.
        TestDomino.objects.get_or_create(nombre=NOMBRE_TEST_DOMINO)
        test_valores, _ = TestValores.objects.get_or_create(
            nombre='Test de Valores de Allport', defaults={'autor': 'Allport'}
        )
        ParteTest.objects.get_or_create(
            test=test_valores, tipo='PRIMERA', defaults={'instrucciones': 'Instrucciones de prueba'}
        )

    def _config(self, **campos):
        ConfiguracionPlataforma.objects.update_or_create(id=1, defaults=campos)

    def _iniciar_sesion(self, usuario, next_url):
        return self.client.post(reverse('core_login'), {
            'username': usuario.username,
            'password': PASSWORD,
            'next': next_url,
        })

    def _autenticado(self):
        return '_auth_user_id' in self.client.session

    # --- Modelo y configuración por defecto ---
    def test_sin_configuracion_se_crea_apagada(self):
        self.assertFalse(ConfiguracionPlataforma.objects.exists())
        self.client.get(reverse('home'))
        config = ConfiguracionPlataforma.objects.get(id=1)
        self.assertFalse(config.pruebas_activas)
        self.assertFalse(config.registro_abierto)

    def test_solo_puede_existir_una_configuracion(self):
        self._config(pruebas_activas=False)
        with self.assertRaises(ValidationError):
            ConfiguracionPlataforma.objects.create()

    # --- Páginas de presentación de cada test: se muestran siempre, ---
    # --- pero cambian el botón según el interruptor ---
    def test_presentacion_con_pruebas_cerradas_oculta_boton_y_avisa(self):
        self._config(pruebas_activas=False)
        self.client.force_login(self.alumno)
        for nombre, texto_boton in self.PAGINAS_DE_PRESENTACION.items():
            with self.subTest(pagina=nombre):
                r = self.client.get(reverse(nombre))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, 'Acceso Bloqueado')
                self.assertNotContains(r, texto_boton)

    def test_presentacion_con_pruebas_abiertas_muestra_boton(self):
        self._config(pruebas_activas=True)
        self.client.force_login(self.alumno)
        for nombre, texto_boton in self.PAGINAS_DE_PRESENTACION.items():
            with self.subTest(pagina=nombre):
                r = self.client.get(reverse(nombre))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, texto_boton)
                self.assertNotContains(r, 'Acceso Bloqueado')

    # --- Inicio de sesión ---
    def test_login_hacia_pruebas_bloquea_alumno_si_estan_cerradas(self):
        self._config(pruebas_activas=False)
        r = self._iniciar_sesion(self.alumno, '/tests/domino/')
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)
        self.assertFalse(self._autenticado())

    def test_login_hacia_pruebas_permite_staff_si_estan_cerradas(self):
        self._config(pruebas_activas=False)
        r = self._iniciar_sesion(self.staff, '/tests/domino/')
        self.assertRedirects(r, '/tests/domino/', fetch_redirect_response=False)
        self.assertTrue(self._autenticado())

    def test_login_hacia_cursos_funciona_con_pruebas_cerradas(self):
        self._config(pruebas_activas=False)
        self._iniciar_sesion(self.alumno, '/cursos/')
        self.assertTrue(self._autenticado())

    def test_login_hacia_pruebas_funciona_si_estan_abiertas(self):
        self._config(pruebas_activas=True)
        self._iniciar_sesion(self.alumno, '/tests/domino/')
        self.assertTrue(self._autenticado())

    # --- Acceso directo por URL al test en sí (no a su presentación) ---
    def test_alumno_no_debe_iniciar_domino_por_url_si_esta_cerrado(self):
        self._config(pruebas_activas=False)
        self.client.raise_request_exception = False
        self.client.force_login(self.alumno)
        r = self.client.get(reverse('tests:test_domino'))
        self.assertIn(r.status_code, (302, 403, 404),
                      'tests:test_domino sigue accesible con las pruebas cerradas')

    def test_staff_puede_iniciar_domino_si_esta_cerrado(self):
        self._config(pruebas_activas=False)
        self.client.force_login(self.staff)
        r = self.client.get(reverse('tests:test_domino'))
        self.assertEqual(r.status_code, 200)

    def test_alumno_puede_iniciar_domino_si_esta_abierto(self):
        self._config(pruebas_activas=True)
        self.client.force_login(self.alumno)
        r = self.client.get(reverse('tests:test_domino'))
        self.assertEqual(r.status_code, 200)

    # --- Decisión de diseño: un resultado ya generado sigue siendo visible ---
    # --- aunque las pruebas estén cerradas (se prueba en AccesoResultadosDominoTests) ---


# ---------------------------------------------------------------------------
# 7. Interruptor registro_abierto (users:signup)
# ---------------------------------------------------------------------------
@override_settings(**AJUSTES_PRUEBA)
class RegistroAbiertoTests(TestCase):
    DATOS_REGISTRO_VALIDOS = {
        'username': 'nuevo_usuario',
        'email': 'nuevo_usuario@example.com',
        'password1': 'ContraseñaSegura2026!',
        'password2': 'ContraseñaSegura2026!',
        'full_name': 'Usuario Nuevo',
        'date_of_birth': '2000-01-01',
        'gender': 'N',
        'institution': '',
        'education_level': '',
        'occupation': '',
    }

    def _config(self, **campos):
        ConfiguracionPlataforma.objects.update_or_create(id=1, defaults=campos)

    def test_registro_cerrado_redirige_al_inicio(self):
        self._config(registro_abierto=False, pruebas_activas=True)
        r = self.client.get(reverse('signup'))
        self.assertRedirects(r, reverse('home'))

    def test_registro_cerrado_no_crea_cuenta_aunque_se_envie_el_formulario(self):
        self._config(registro_abierto=False, pruebas_activas=True)
        self.client.post(reverse('signup'), self.DATOS_REGISTRO_VALIDOS)
        self.assertFalse(User.objects.filter(username='nuevo_usuario').exists())

    def test_registro_abierto_permite_crear_cuenta(self):
        self._config(registro_abierto=True, pruebas_activas=True)
        r = self.client.post(reverse('signup'), self.DATOS_REGISTRO_VALIDOS)
        self.assertTrue(User.objects.filter(username='nuevo_usuario').exists())
        self.assertRedirects(r, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_registro_con_correo_duplicado_no_crea_cuenta(self):
        self._config(registro_abierto=True, pruebas_activas=True)
        crear_usuario('quien_ya_existe', email='nuevo_usuario@example.com')
        datos = {**self.DATOS_REGISTRO_VALIDOS, 'username': 'otro_username'}
        self.client.post(reverse('signup'), datos)
        self.assertFalse(User.objects.filter(username='otro_username').exists())

    def test_registro_con_password_numerica_no_crea_cuenta(self):
        self._config(registro_abierto=True, pruebas_activas=True)
        datos = {**self.DATOS_REGISTRO_VALIDOS, 'password1': '12345678', 'password2': '12345678'}
        self.client.post(reverse('signup'), datos)
        self.assertFalse(User.objects.filter(username='nuevo_usuario').exists())

    # --- Decisión de diseño confirmada: la página de registro (base.html) ---
    # --- también depende de pruebas_activas, independientemente de registro_abierto ---
    def test_registro_abierto_pero_pruebas_inactivas_muestra_mantenimiento(self):
        self._config(registro_abierto=True, pruebas_activas=False)
        r = self.client.get(reverse('signup'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Plataforma en Mantenimiento')
        self.assertNotContains(r, 'Crear Nueva Cuenta')

    def test_registro_abierto_y_pruebas_activas_muestra_formulario(self):
        self._config(registro_abierto=True, pruebas_activas=True)
        r = self.client.get(reverse('signup'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Crear Nueva Cuenta')
        self.assertNotContains(r, 'Plataforma en Mantenimiento')