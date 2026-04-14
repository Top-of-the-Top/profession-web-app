from datetime import timedelta
from pathlib import Path
import os
import sys
from dotenv import load_dotenv
import tempfile

load_dotenv()

ALLOWED_HOSTS = ['professionkid.ru', 'https://professionkid.ru']


BASE_DIR = Path(__file__).resolve().parent.parent

ASGI_APPLICATION = "project.asgi.application"

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-ci-secret-key-for-tests-only')

DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.users.apps.UsersConfig',
    'apps.core.apps.CoreConfig',
    'apps.carts.apps.CartConfig',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'apps.courses.apps.CoursesConfig',
    'apps.payments.apps.PaymentsConfig',
    'drf_spectacular',
    'storages',
    'django_celery_results',
    'apps.notifications.apps.NotificationsConfig',
    'sms',
    'apps.homeworks.apps.HomeworksConfig',
    'apps.webinars.apps.WebinarsConfig',
    'apps.ai_chat_bot.apps.AiChatBotConfig',
]

USE_S3 = os.environ.get('USE_S3', 'False') == 'True'
CORS_ALLOW_ALL_ORIGINS = True

MIDDLEWARE = [
    'project.middleware.RequestTimingMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'crum.CurrentRequestUserMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
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

if os.getenv('CI') or 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'test_db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'postgres'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

SPECTACULAR_SETTINGS = {
    'TITLE': 'My Profession Web App API',
    'DESCRIPTION': 'API для вашего проекта',
    'VERSION': '1.0.0',
    'TAGS': [
        {
            'name': 'Landing',
            'description': 'Публичный лендинг: превью списка курсов.',
        },
        {
            'name': 'Home',
            'description': 'Домашний экран приложения: купленные курсы пользователя.',
        },
        {
            'name': 'Course',
            'description': 'Каталог и карточка курса, главная курса, секции и уроки.',
        },
        {
            'name': 'Homework',
            'description': 'Домашние задания, задачи и вопросы (вложенные в урок).',
        },
        {
            'name': 'Users',
            'description': 'Пользователи, регистрация, профиль и роли.',
        },
        {
            'name': 'Carts',
            'description': 'Корзина и связанные с ней операции.',
        },
        {
            'name': 'Payments',
            'description': 'Оплата и платёжные сценарии.',
        },
        {
            'name': 'Notifications',
            'description': 'Уведомления пользователя: список и поток SSE.',
        },
    ],
    'POSTPROCESSING_HOOKS': [
        'project.openapi_hooks.canonicalize_tags',
    ],
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'users.User'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'webmaster@localhost')


SMS_BACKEND = os.getenv('SMS_BACKEND', 'sms.backends.console.SmsBackend')
DEFAULT_FROM_SMS = os.getenv('DEFAULT_FROM_SMS', '+1234567890')
NOTIFICORE_API_KEY = os.getenv('NOTIFICORE_API_KEY', '')
NOTIFICORE_API_URL = os.getenv('NOTIFICORE_API_URL', '')

if USE_S3:
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', 'https://storage.yandexcloud.net')
    AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ru-central1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "bucket_name": AWS_S3_BUCKET_NAME,
                "region_name": AWS_S3_REGION_NAME,
                "default_acl": "public-read-write",
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
    MEDIA_URL = f'https://storage.yandexcloud.net/{os.getenv("AWS_S3_BUCKET_NAME", "")}/media/'
    STATIC_URL = f'https://storage.yandexcloud.net/{os.getenv("AWS_S3_BUCKET_NAME", "")}/static/'
else:
    MEDIA_URL = '/media/'
    STATIC_URL = '/static/'

CELERY_BEAT_SCHEDULE = {
    'check-idle-webinars': {
        'task': 'apps.courses.tasks.check_idle_webinars',
        'schedule': 60.0,
    },
}

if os.getenv('CI') or 'test' in sys.argv:
    MEDIA_ROOT=tempfile.mkdtemp()
    CELERY_TASK_ALWAYS_EAGER=True
    CELERY_TASK_EAGER_PROPAGATES=True
    BROKER_BACKEND='memory'
    CELERY_BROKER_URL='memory://'
else:
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//')
    CELERY_RESULT_BACKEND = 'django-db'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_TASK_TRACK_STARTED = True

RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672//')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {'format': '{message}', 'style': '{'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django.server': {'handlers': ['console'], 'level': 'CRITICAL', 'propagate': False},
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'daphne': {'handlers': ['console'], 'level': 'CRITICAL', 'propagate': False},
        'twisted': {'handlers': ['console'], 'level': 'CRITICAL', 'propagate': False},
    },
}

REDIS_PASS = os.getenv('REDIS_PASS', '')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')  # Имя сервиса в docker-compose
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_KEY_PREFIX = os.getenv('REDIS_KEY_PREFIX', '')
REDIS_BASE_URL = f'redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}'

if os.getenv('CI') or 'test' in sys.argv:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/django_test_cache',
            'TIMEOUT': 60,
            'OPTIONS': {
                'MAX_ENTRIES': 100,
            }
        },
        'hot': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/django_test_hot_cache',
            'TIMEOUT': 10,
        },
        'cold': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/django_test_cold_cache',
            'TIMEOUT': 300,
        },
        'landing': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/django_test_landing_cache',
            'TIMEOUT': 600,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'{REDIS_BASE_URL}/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'PASSWORD': REDIS_PASS,
                'SOCKET_CONNECT_TIMEOUT': 5, # Это таймаут на подключение
                'SOCKET_TIMEOUT': 5, #  Это таймаут на чтение-запись
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 100,
                    'retry_on_timeout': True,
                    'socket_keepalive': True,
                }
            },
            'KEY_PREFIX': REDIS_KEY_PREFIX,
            'TIMEOUT': 600, # Время жизни кэша
        },
        'hot': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'{REDIS_BASE_URL}/0',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'PASSWORD': REDIS_PASS,
                'SOCKET_CONNECT_TIMEOUT': 5,  # Это таймаут на подключение
                'SOCKET_TIMEOUT': 5,  # Это таймаут на чтение-запись
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 100,
                    'retry_on_timeout': True,
                    'socket_keepalive': True,
                }
            },
            'KEY_PREFIX': REDIS_KEY_PREFIX,
            'TIMEOUT': 60,
        },
        'cold': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'{REDIS_BASE_URL}/2',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'PASSWORD': REDIS_PASS,
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 100,
                    'retry_on_timeout': True,
                    'socket_keepalive': True,
                }
            },
            'KEY_PREFIX': REDIS_KEY_PREFIX,
            'TIMEOUT': 3600,  # Время жизни кэша
        },
    }