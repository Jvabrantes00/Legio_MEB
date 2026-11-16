import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = 'test-only-key-not-for-production'
JWT_SIGNING_KEY = 'test-only-jwt-key-not-for-production'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost']
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'core', 'rest_framework', 'rest_framework_simplejwt.token_blacklist',
    'corsheaders', 'django_filters',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'setup.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
              'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request',
                  'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages',
              ]}}]
WSGI_APPLICATION = 'setup.wsgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'HOST': os.environ['PGHOST'], 'PORT': os.environ['PGPORT'],
    'USER': os.environ['PGUSER'], 'PASSWORD': os.environ['PGPASSWORD'],
    'NAME': os.environ['PGDATABASE'],
}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

CORS_ALLOWED_ORIGINS = []
CORS_ALLOWED_ORIGIN_REGEXES = []
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt',
    'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]
CSRF_TRUSTED_ORIGINS = []

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('core.permissions.HasAnySiaRole',),
    'DEFAULT_THROTTLE_RATES': {
        'public_registration_read': '60/minute',
        'public_registration_submit': '10/minute',
        'public_invitation': '10/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': JWT_SIGNING_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

SIA_INVITATION_OUTBOX_KEY = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='
SIA_PUBLIC_INVITATION_BASE_URL = 'http://testserver/convites'
SIA_INVITATION_EMAIL_BACKEND = 'smtp'
SIA_SMTP_HOST = ''
SIA_SMTP_PORT = 25
SIA_SMTP_USERNAME = ''
SIA_SMTP_PASSWORD = ''
SIA_SMTP_FROM_EMAIL = ''
SIA_SMTP_USE_TLS = False
SIA_SMTP_USE_SSL = False
SIA_SMTP_TIMEOUT = 10
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SIA_WHATSAPP_BACKEND = 'mock'
SIA_WHATSAPP_MOCK_MODE = 'sucesso'

CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
SIA_CELERY_OUTBOX_INTERVAL = 300
SIA_CELERY_CAMPAIGN_INTERVAL = 300
CELERY_BEAT_SCHEDULE = {
    'reconciliar-outbox-convites': {
        'task': 'core.reconciliar_outboxes_convites',
        'schedule': SIA_CELERY_OUTBOX_INTERVAL,
    },
    'processar-prazos-campanhas': {
        'task': 'core.processar_prazos_campanhas',
        'schedule': SIA_CELERY_CAMPAIGN_INTERVAL,
    },
    'processar-sinais-reposicao': {
        'task': 'core.processar_sinais_reposicao',
        'schedule': SIA_CELERY_CAMPAIGN_INTERVAL,
    },
}
