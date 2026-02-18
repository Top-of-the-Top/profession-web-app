from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent



SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.users.apps.UsersConfig',
    'apps.cart.apps.CartConfig',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders', # для CORS. Разрешает браузерам делать запросы к API с других доменов
    'apps.courses.apps.CoursesConfig',
    'apps.payments.apps.PaymentsConfig',
    'drf_spectacular',
    'storages',
    'django_celery_results', # Это табличка для результатов выполнения задач Celery
]
USE_S3 = os.environ.get('USE_S3') == 'True'


CORS_ALLOW_ALL_ORIGINS = True # Для разработки, потом поменяем. В проде нужен будет явный список

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    # Настройки для безопасности
    'ROTATE_REFRESH_TOKENS': True,  # При обновлении выдается новый refresh токен
    'BLACKLIST_AFTER_ROTATION': False,  # True требует rest_framework_simplejwt.token_blacklist в INSTALLED_APPS
    'UPDATE_LAST_LOGIN': True,  # Обновляет last_login при аутентификации
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
import dj_database_url
import os
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=False,
    )
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'My Profession Web App API',
    'DESCRIPTION': 'API для вашего проекта',
    'VERSION': '1.0.0',  # <--- Обязательное поле!
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = 'users.User' # Это указание на кастомную модель пользователя вместо стандартной


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Настройки smtp сервера
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT'))

EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL') == 'True'

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL')

# Настройки S3 Yandex Cloud Storage
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",  # ← Внимание: S3Storage, не S3Boto3Storage!
        "OPTIONS": {
            "access_key": os.getenv('AWS_ACCESS_KEY_ID'),
            "secret_key": os.getenv('AWS_SECRET_ACCESS_KEY'),
            "endpoint_url": os.getenv('AWS_S3_ENDPOINT_URL', 'https://storage.yandexcloud.net'),
            "bucket_name": os.getenv('AWS_S3_BUCKET_NAME'),
            "region_name": os.getenv('AWS_S3_REGION_NAME', 'ru-central1'),
            "default_acl": "public-read-write",  # ← Лучше чем public-read-write
            "querystring_auth": False,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": os.getenv('AWS_ACCESS_KEY_ID'),
            "secret_key": os.getenv('AWS_SECRET_ACCESS_KEY'),
            "endpoint_url": os.getenv('AWS_S3_ENDPOINT_URL', 'https://storage.yandexcloud.net'),
            "bucket_name": os.getenv('AWS_S3_BUCKET_NAME'),
            "region_name": os.getenv('AWS_S3_REGION_NAME', 'ru-central1'),
            "default_acl": "public-read",
            "querystring_auth": False,
        },
    }
}

MEDIA_URL = f'https://storage.yandexcloud.net/{os.getenv("AWS_S3_BUCKET_NAME")}/media/'
STATIC_URL = f'https://storage.yandexcloud.net/{os.getenv("AWS_S3_BUCKET_NAME")}/static/'


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True