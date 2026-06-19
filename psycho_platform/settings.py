from pathlib import Path

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
    'django.contrib.staticfiles',
    'ckeditor',
    'embed_video',
    'core',
    'courses',
    'tests',
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@centrodhae.com'
ADMIN_EMAIL = 'admin@centrodhae.com'   # cámbialo por el email real

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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # 
