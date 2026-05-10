import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

ASGI_APPLICATION = "project.asgi.application"

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-ci-secret-key-for-tests-only")

DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost,http://127.0.0.1,https://professionkid-testing.ru,http://professionkid-testing.ru",
    ).split(",")
    if origin.strip()
]

STATISTICS_WEBINAR_THRESHOLD = 0.7

INSTALLED_APPS = [
    "daphne",
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.users.apps.UsersConfig",
    "apps.core.apps.CoreConfig",
    "apps.carts.apps.CartConfig",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.courses.apps.CoursesConfig",
    "apps.payments.apps.PaymentsConfig",
    "drf_spectacular",
    "storages",
    "apps.notifications.apps.NotificationsConfig",
    "sms",
    "apps.homeworks.apps.HomeworksConfig",
    "apps.webinars.apps.WebinarsConfig",
    "apps.ai_chat_bot.apps.AiChatBotConfig",
    "apps.admin_panel.apps.AdminPanelConfig",
    "apps.stats",
    "apps.applications.apps.ApplicationsConfig",
]

USE_S3 = os.environ.get("USE_S3", "False") == "True"
CORS_ALLOW_ALL_ORIGINS = True

MIDDLEWARE = [
    "project.middleware.RequestTimingMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "crum.CurrentRequestUserMiddleware",
]

if DEBUG:
    INSTALLED_APPS += ["orbit"]
    MIDDLEWARE = ["orbit.middleware.OrbitMiddleware"] + MIDDLEWARE

    ORBIT_CONFIG = {
        "ENABLED": True,
        "SLOW_QUERY_THRESHOLD_MS": 200,
        "STORAGE_LIMIT": 2000,
        "AUTH_CHECK": lambda request: True,
        "IGNORE_PATHS": ["/orbit/", "/static/", "/media/", "/api/schema/"],
        "WATCHER_FAIL_SILENTLY": True,
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

if os.getenv("CI") or "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "test_db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 0,
            "OPTIONS": {
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000",
            },
        }
    }

SPECTACULAR_SETTINGS = {
    "TITLE": "Профессия — API",
    "DESCRIPTION": (
        "«Профессия» — образовательная онлайн-платформа для проведения структурированных курсов "
        "с видеосвязью, интерактивной доской и встроенным ИИ-помощником.\n\n"
        "Платформа объединяет каталог платных курсов, онлайн-вебинары, просмотр записей, "
        "домашние задания с автоматической и ручной проверкой, а также специальные курсы "
        "по приглашению преподавателя — без оплаты и без отображения в общем каталоге.\n\n"
        "**Аутентификация**\n\n"
        "Все защищённые эндпоинты принимают JWT-токен в заголовке:\n\n"
        "```\nAuthorization: Bearer <access_token>\n```\n\n"
        "Токены выдаются при входе, регистрации и OAuth-авторизации. "
        "Обновление — через `POST /api/v1/refresh/`.\n\n"
        "**Роли пользователей**\n\n"
        "| Роль | Описание |\n"
        "|------|----------|\n"
        "| `student` | Покупает курсы, выполняет задания, смотрит вебинары |\n"
        "| `teacher` | Ведёт курсы, проводит вебинары, проверяет задания |\n"
        "| `moderator` | Полный доступ ко всем операциям платформы |\n\n"
        "**Формат ошибок**\n\n"
        "Все бизнес-ошибки возвращаются в едином формате:\n\n"
        "```json\n"
        "{\n"
        '  "status": "error",\n'
        '  "code": "COURSE_NOT_FOUND",\n'
        '  "message": "Курс не найден.",\n'
        '  "details": {}\n'
        "}\n"
        "```"
    ),
    "VERSION": "1.0.0",
    "TAGS": [
        {
            "name": "Landing",
            "description": "Публичные эндпоинты для лендинга. Не требуют авторизации.",
        },
        {
            "name": "Users",
            "description": (
                "Регистрация, вход, сброс пароля, управление профилем. "
                "Поддерживается авторизация через email, телефон, Яндекс и ВКонтакте."
            ),
        },
        {
            "name": "Course",
            "description": (
                "Каталог курсов, карточка курса, структура (секции и уроки). "
                "Редактирование доступно автору курса и модератору."
            ),
        },
        {
            "name": "Homework",
            "description": (
                "Домашние задания, задачи с развёрнутым ответом и вопросы с вариантами. "
                "Студент сдаёт попытку, преподаватель проверяет и выставляет баллы."
            ),
        },
        {
            "name": "Webinar",
            "description": (
                "Управление вебинарами: запуск, остановка, расписание, подключение участников. "
                "Запись через Agora Cloud Recording с последующей загрузкой в Kinescope."
            ),
        },
        {
            "name": "Carts",
            "description": "Корзина покупок: добавление и удаление курсов, оплата.",
        },
        {
            "name": "Payments",
            "description": "История платежей и детали конкретного платежа.",
        },
        {
            "name": "Applications",
            "description": (
                "Заявки на специальные курсы. Студент подаёт заявку, "
                "преподаватель или модератор одобряет или отклоняет её."
            ),
        },
        {
            "name": "Notifications",
            "description": (
                "Уведомления пользователя: постраничный список и real-time поток "
                "через Server-Sent Events."
            ),
        },
        {
            "name": "Statistics",
            "description": (
                "Аналитика для преподавателей и модераторов: посещаемость вебинаров, "
                "прогресс студентов, сводные таблицы по курсам и преподавателям."
            ),
        },
        {
            "name": "Admin Panel",
            "description": (
                "Инструменты модератора: управление преподавателями на курсах, "
                "публикация курсов, приглашения для регистрации новых преподавателей."
            ),
        },
        {
            "name": "Assets",
            "description": (
                "Загрузка медиафайлов в S3: инициация загрузки, получение presigned URL "
                "и проверка статуса ассета."
            ),
        },
    ],
    "POSTPROCESSING_HOOKS": [
        "project.openapi_hooks.canonicalize_tags",
    ],
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.User"
STATIC_ROOT = BASE_DIR / "staticfiles"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "webmaster@localhost")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "webmaster@localhost")
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "http://localhost:3000")


SMS_BACKEND = os.getenv("SMS_BACKEND", "sms.backends.console.SmsBackend")
DEFAULT_FROM_SMS = os.getenv("DEFAULT_FROM_SMS", "+1234567890")
NOTIFICORE_API_KEY = os.getenv("NOTIFICORE_API_KEY", "")
NOTIFICORE_API_URL = os.getenv("NOTIFICORE_API_URL", "")

KINESCOPE_API_TOKEN = os.getenv("KINESCOPE_API_TOKEN", "")
KINESCOPE_PROJECT_ID = os.getenv("KINESCOPE_PROJECT_ID", "")
ASSET_S3_EVENT_QUEUE_URL = os.getenv("ASSET_S3_EVENT_QUEUE_URL", "")

if USE_S3:
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
    AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ru-central1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
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
                "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
                "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL", "https://storage.yandexcloud.net"),
                "bucket_name": os.getenv("AWS_S3_BUCKET_NAME"),
                "region_name": os.getenv("AWS_S3_REGION_NAME", "ru-central1"),
                "default_acl": "public-read",
                "querystring_auth": False,
            },
        },
    }
    MEDIA_URL = f"https://storage.yandexcloud.net/{os.getenv('AWS_S3_BUCKET_NAME', '')}/media/"
    STATIC_URL = f"https://storage.yandexcloud.net/{os.getenv('AWS_S3_BUCKET_NAME', '')}/static/"
else:
    MEDIA_URL = "/media/"
    STATIC_URL = "/static/"

CELERY_BEAT_SCHEDULE = {
    "check-idle-webinars": {
        "task": "apps.webinars.tasks.check_idle_webinars",
        "schedule": 60.0,
    },
    "assets-poll-s3-events": {
        "task": "apps.core.meta_management.tasks.poll_s3_upload_events",
        "schedule": 30.0,
    },
    "assets-sweep-pending": {
        "task": "apps.core.meta_management.tasks.sweep_pending_assets",
        "schedule": 600.0,
    },
    "assets-sweep-orphaned": {
        "task": "apps.core.meta_management.tasks.sweep_orphaned_assets",
        "schedule": 3600.0,
    },
}

if os.getenv("CI") or "test" in sys.argv:
    MEDIA_ROOT = tempfile.mkdtemp()
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    BROKER_BACKEND = "memory"
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
else:
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_TIMEZONE = TIME_ZONE


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//")


REDIS_PASS = os.getenv("REDIS_PASS", "")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "")
REDIS_BASE_URL = f"redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}"

if os.getenv("CI") or "test" in sys.argv:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": "/tmp/django_test_cache",
            "TIMEOUT": 60,
            "OPTIONS": {
                "MAX_ENTRIES": 100,
            },
        },
        "hot": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": "/tmp/django_test_hot_cache",
            "TIMEOUT": 10,
        },
        "cold": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": "/tmp/django_test_cold_cache",
            "TIMEOUT": 300,
        },
        "landing": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": "/tmp/django_test_landing_cache",
            "TIMEOUT": 600,
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_BASE_URL}/1",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": REDIS_PASS,
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 100,
                    "retry_on_timeout": True,
                    "socket_keepalive": True,
                },
            },
            "KEY_PREFIX": REDIS_KEY_PREFIX,
            "TIMEOUT": 600,
        },
        "hot": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_BASE_URL}/0",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": REDIS_PASS,
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 100,
                    "retry_on_timeout": True,
                    "socket_keepalive": True,
                },
            },
            "KEY_PREFIX": REDIS_KEY_PREFIX,
            "TIMEOUT": 60,
        },
        "cold": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_BASE_URL}/2",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": REDIS_PASS,
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 100,
                    "retry_on_timeout": True,
                    "socket_keepalive": True,
                },
            },
            "KEY_PREFIX": REDIS_KEY_PREFIX,
            "TIMEOUT": 3600,
        },
    }


YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "")
YANDEX_ASSISTANT_ID = os.getenv("YANDEX_ASSISTANT_ID", "")


YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "")
YANDEX_REDIRECT_URI = os.getenv("YANDEX_REDIRECT_URI", "")
FRONTEND_OAUTH_YANDEX_REDIRECT_URI = os.getenv("FRONTEND_OAUTH_YANDEX_REDIRECT_URI", "")

VK_CLIENT_ID = os.getenv("VK_CLIENT_ID", "")
VK_CLIENT_SECRET = os.getenv("VK_CLIENT_SECRET", "")
VK_REDIRECT_URI = os.getenv("VK_REDIRECT_URI", "")
FRONTEND_OAUTH_VK_REDIRECT_URI = os.getenv("FRONTEND_OAUTH_VK_REDIRECT_URI", "")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}

UNFOLD = {
    "SITE_TITLE": "Профессия — Панель управления",
    "SITE_HEADER": "Профессия — Панель управления",
    "SITE_URL": "/",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Главная",
                "separator": False,
                "items": [
                    {
                        "title": "Дашборд",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "Пользователи",
                "separator": True,
                "items": [
                    {
                        "title": "Пользователи",
                        "icon": "person",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Профили",
                        "icon": "manage_accounts",
                        "link": "/admin/users/profile/",
                    },
                    {
                        "title": "Приглашения",
                        "icon": "mail",
                        "link": "/admin/admin_panel/invitation/",
                    },
                ],
            },
            {
                "title": "Обучение",
                "separator": True,
                "items": [
                    {
                        "title": "Курсы",
                        "icon": "menu_book",
                        "link": "/admin/courses/course/",
                    },
                    {
                        "title": "Секции",
                        "icon": "folder_open",
                        "link": "/admin/courses/section/",
                    },
                    {
                        "title": "Уроки",
                        "icon": "play_lesson",
                        "link": "/admin/courses/lesson/",
                    },
                    {
                        "title": "Купленные курсы",
                        "icon": "shopping_bag",
                        "link": "/admin/courses/purchasedcourse/",
                    },
                ],
            },
            {
                "title": "Домашние задания",
                "separator": True,
                "items": [
                    {
                        "title": "Домашние задания",
                        "icon": "assignment",
                        "link": "/admin/courses/homework/",
                    },
                    {
                        "title": "Вопросы",
                        "icon": "help_outline",
                        "link": "/admin/courses/question/",
                    },
                    {
                        "title": "Задания",
                        "icon": "edit_note",
                        "link": "/admin/courses/task/",
                    },
                    {
                        "title": "Попытки",
                        "icon": "rate_review",
                        "link": "/admin/homeworks/attempt/",
                    },
                    {
                        "title": "Ответы на вопросы",
                        "icon": "quiz",
                        "link": "/admin/homeworks/questionanswer/",
                    },
                    {
                        "title": "Ответы на задания",
                        "icon": "task_alt",
                        "link": "/admin/homeworks/taskanswer/",
                    },
                    {
                        "title": "Ревью заданий",
                        "icon": "grading",
                        "link": "/admin/homeworks/taskreview/",
                    },
                ],
            },
            {
                "title": "Финансы",
                "separator": True,
                "items": [
                    {
                        "title": "Платежи",
                        "icon": "payments",
                        "link": "/admin/payments/payment/",
                    },
                    {
                        "title": "Корзины",
                        "icon": "shopping_cart",
                        "link": "/admin/carts/cart/",
                    },
                    {
                        "title": "Товары в корзинах",
                        "icon": "add_shopping_cart",
                        "link": "/admin/carts/cartitem/",
                    },
                ],
            },
            {
                "title": "Вебинары",
                "separator": True,
                "items": [
                    {
                        "title": "Вебинары",
                        "icon": "videocam",
                        "link": "/admin/webinars/webinar/",
                    },
                    {
                        "title": "Записи",
                        "icon": "video_library",
                        "link": "/admin/webinars/recording/",
                    },
                ],
            },
            {
                "title": "Аналитика",
                "separator": True,
                "items": [
                    {
                        "title": "Прогресс по урокам",
                        "icon": "trending_up",
                        "link": "/admin/stats/lessonprogress/",
                    },
                    {
                        "title": "Посещения вебинаров",
                        "icon": "groups",
                        "link": "/admin/stats/webinarattendance/",
                    },
                    {
                        "title": "Просмотры записей",
                        "icon": "ondemand_video",
                        "link": "/admin/stats/recordingview/",
                    },
                ],
            },
            {
                "title": "Уведомления и чат",
                "separator": True,
                "items": [
                    {
                        "title": "Уведомления",
                        "icon": "notifications",
                        "link": "/admin/notifications/notification/",
                    },
                    {
                        "title": "AI-сессии",
                        "icon": "smart_toy",
                        "link": "/admin/ai_chat_bot/session/",
                    },
                    {
                        "title": "AI-чаты",
                        "icon": "chat",
                        "link": "/admin/ai_chat_bot/chat/",
                    },
                    {
                        "title": "AI-сообщения",
                        "icon": "forum",
                        "link": "/admin/ai_chat_bot/message/",
                    },
                ],
            },
            {
                "title": "Медиа",
                "separator": True,
                "items": [
                    {
                        "title": "Медиа-активы",
                        "icon": "perm_media",
                        "link": "/admin/core/mediaasset/",
                    },
                    {
                        "title": "Использование медиа",
                        "icon": "link",
                        "link": "/admin/core/assetusage/",
                    },
                ],
            },
        ],
    },
    "DASHBOARD_CALLBACK": "project.dashboard.dashboard_callback",
    "STYLES": [],
    "SCRIPTS": [],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "ignore_cancelled": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: "CancelledError" not in record.getMessage(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["ignore_cancelled"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
