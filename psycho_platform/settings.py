from pathlib import Path
import dj_database_url

import os
import cloudinary

BASE_DIR = Path(__file__).resolve().parent.parent 
print("BASE_DIR:", BASE_DIR)
print("Templates path:", BASE_DIR / 'templates')


SECRET_KEY = 'django-insecure-76l$=a@sb41v+p3*w69w(ix-c5zjgit)@#!r%pwb=j98vs4(vm'

DEBUG = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',  # ← primero staticfiles
    'cloudinary_storage',          # ← después
    'cloudinary',
    'ckeditor',
    'embed_video',
    'core',
    'courses',
    'tests',
    'users',
    'panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # ← esta línea falta
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'psycho_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'panel.context_processors.panel_roles',
                'core.context_processors.config_global',
                'core.context_processors.plantilla_base_dinamica',
            ],
        },
        'DIRS': [
            BASE_DIR / 'templates',
        ],
    },
]

WSGI_APPLICATION = 'psycho_platform.wsgi.application'


# Database

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql',
#        'NAME': 'psyco',
#        'USER': 'postgres',
#        'PASSWORD': 'hangar81',
#        'HOST': 'localhost',  # O la dirección de tu servidor de base de datos
#        'PORT': '5432',       # Puerto por defecto de PostgreSQL
#    }
#}
DATABASES = {
    'default': dj_database_url.config(
        default=f"postgresql://neondb_owner:npg_QsjPqh9t1oYr@ep-crimson-band-a6g42xbo-pooler.us-west-2.aws.neon.tech/neondb",
        conn_max_age=600,
        ssl_require=True  # Neon y Railway pueden requerir SSL
    )
}

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

CKEDITOR_UPLOAD_PATH = "uploads/"

# settings.py

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        'toolbar': 'dhae_toolbar',
        'toolbar_dhae_toolbar': [
            # Fila 1: fuente, tamaño, estilos básicos
            ['Font', 'FontSize'],
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['TextColor', 'BGColor'],
            '/',  # salto de fila
            # Fila 2: párrafo y listas
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight'],
            ['Link', 'Unlink'],
            ['Image', 'Table', 'HorizontalRule'],
            ['RemoveFormat', 'Maximize'],
            # Sin 'Source' (Fuente HTML) ni 'Styles'
        ],
        'font_names': (
            'Arial/Arial, Helvetica, sans-serif;'
            'Calibri/Calibri, sans-serif;'
            'Georgia/Georgia, serif;'
            'Times New Roman/Times New Roman, Times, serif;'
            'Verdana/Verdana, Geneva, sans-serif;'
            'Trebuchet MS/Trebuchet MS, Helvetica, sans-serif;'
        ),
        'fontSize_sizes': '10/10px;11/11px;12/12px;14/14px;16/16px;18/18px;20/20px;24/24px;28/28px;36/36px',
        'width': '100%',
        'height': 300,
        'removePlugins': 'stylesheetparser,exportpdf',
        'extraPlugins': 'font',         # necesario para el combo Font
        'removeButtons': '',
        'forcePasteAsPlainText': False,
        'allowedContent': True,         # permite todo el HTML que genere el editor
    }
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.CustomUser'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
LOGIN_REDIRECT_URL = 'tests:index'
LOGIN_REDIRECT_URL = 'tests:index'
LOGIN_URL = '/login/'

# Configuración de email para desarrollo (verás los correos en la consola)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'contacto.centrodhae@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'odup duin ixxe wrdfs')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
CONTACT_FORM_RECIPIENT = 'magnesyst@centrodhae.com'  # Dirección que recibirá los mensajes del formulario

ADMIN_EMAIL = 'magnesyst@gmail.com'

SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

# Añade al final del archivo
# Pon esto:
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# Esto hace que todos los uploads vayan a Cloudinary
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
