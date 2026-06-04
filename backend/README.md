# Серверная часть приложения Profession Web App

Django 6 API для платформы «Профессия»: REST, JWT, WebSocket (ИИ-чат), фоновые задачи Celery, админка Unfold.

Корневой README и Docker Compose — в [корне монорепы](../README.md).

---

## Стек технологий

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,django,postgres,redis,docker&theme=dark" alt="Python, Django, PostgreSQL, Redis, Docker" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Django-6-092E20?style=flat-square&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/DRF-REST-092E20?style=flat-square&logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/Daphne-ASGI-092E20?style=flat-square&logo=django&logoColor=white" alt="Daphne" />
  <img src="https://img.shields.io/badge/Channels-WebSocket-092E20?style=flat-square&logo=django&logoColor=white" alt="Channels" />
  <img src="https://img.shields.io/badge/SimpleJWT-auth-000000?style=flat-square&logo=jsonwebtokens&logoColor=white" alt="JWT" />
  <img src="https://img.shields.io/badge/Celery-Beat-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/RabbitMQ-broker-FF6600?style=flat-square&logo=rabbitmq&logoColor=white" alt="RabbitMQ" />
  <img src="https://img.shields.io/badge/drf--spectacular-OpenAPI-6C63FF?style=flat-square" alt="OpenAPI" />
</p>

| Слой | Пакеты |
|------|--------|
| HTTP / WS | Daphne, Django Channels, `channels-redis` |
| API | Django REST Framework, `drf-spectacular` |
| Auth | `rest_framework_simplejwt`, OAuth (Яндекс, ВК) |
| Очереди | Celery, RabbitMQ, Redis (results) |
| Файлы | `django-storages`, S3 (Yandex Object Storage) |
| Admin | `django-unfold` |
| Dev | `django-orbit` (профилирование при `DEBUG=True`) |

---

## Архитектура серверной части

```mermaid
flowchart TB
  subgraph L1["① Клиенты"]
    direction LR
    SPA["React SPA"]
    ADM["Django Admin · Unfold"]
  end

  subgraph L2["② Точка входа · project/asgi.py"]
    DAPHNE["Daphne ASGI<br/>ProtocolTypeRouter"]
  end

  subgraph L3["③ Конвейер запросов"]
    direction LR
    HTTP_PIPE["HTTP<br/>Security · CORS · Session<br/>JWT · Timing · Orbit"]
    WS_PIPE["WebSocket<br/>JWT Auth Middleware"]
  end

  subgraph L4["④ Публичные интерфейсы"]
    direction TB
    REST["REST API<br/>/api/v1/ · OpenAPI"]
    SSE["Server-Sent Events<br/>notifications/sse/"]
    WS_AI["WebSocket<br/>ai_chat_bot"]
    META["Health · Swagger<br/>/admin/"]
  end

  subgraph L5["⑤ Доменный слой · apps/"]
    direction TB

    subgraph D_AUTH["Доступ"]
      users["users<br/>JWT · OAuth · профиль"]
    end

    subgraph D_LEARN["Обучение"]
      direction LR
      courses["courses"]
      homeworks["homeworks"]
      webinars["webinars"]
      applications["applications"]
    end

    subgraph D_SHOP["Коммерция"]
      direction LR
      carts["carts"]
      payments["payments"]
    end

    subgraph D_PLATFORM["Платформа"]
      direction LR
      core["core<br/>media assets"]
      notifications["notifications"]
      ai_chat["ai_chat_bot"]
      admin_panel["admin_panel"]
      stats["stats"]
    end
  end

  subgraph L6["⑥ Фоновая обработка"]
    direction LR
    BEAT["Celery Beat<br/>расписание"]
    WORKER["Celery Worker<br/>tasks"]
    TASKS["webinars · core/assets<br/>idle · S3 sweep"]
  end

  subgraph L7["⑦ Персистентность"]
    direction LR
    PG[("PostgreSQL<br/>основные данные")]
    REDIS[("Redis<br/>cache hot/default/cold<br/>Channels · Celery results")]
    RMQ["RabbitMQ<br/>Celery broker<br/>notifications exchange"]
    S3[("S3<br/>media · static")]
  end

  subgraph L8["⑧ Внешние интеграции"]
    direction LR
    AGORA["Agora<br/>RTC · доска · запись"]
    KINE["Kinescope<br/>хостинг записей"]
    YGPT["Yandex GPT<br/>ИИ-ответы"]
    OAUTH["OAuth<br/>Яндекс · ВК"]
    COMMS["SMTP · SMS<br/>Notificore"]
  end

  SPA --> DAPHNE
  ADM --> DAPHNE

  DAPHNE --> HTTP_PIPE
  DAPHNE --> WS_PIPE

  HTTP_PIPE --> REST
  HTTP_PIPE --> SSE
  HTTP_PIPE --> META
  WS_PIPE --> WS_AI

  REST --> D_AUTH
  REST --> D_LEARN
  REST --> D_SHOP
  REST --> D_PLATFORM
  SSE --> notifications
  WS_AI --> ai_chat

  D_AUTH --> PG
  D_LEARN --> PG
  D_SHOP --> PG
  D_PLATFORM --> PG

  D_LEARN --> REDIS
  D_PLATFORM --> REDIS
  core --> S3
  webinars --> S3

  users --> OAUTH
  users --> COMMS
  notifications --> COMMS
  ai_chat --> YGPT
  webinars --> AGORA
  webinars --> KINE

  REST -.->|события| RMQ
  notifications -.->|publish| RMQ

  BEAT -->|cron| RMQ
  RMQ --> WORKER
  WORKER --> TASKS
  TASKS --> PG
  TASKS --> S3
  TASKS --> KINE
  TASKS --> REDIS

  classDef layerClient fill:#e0f2fe,stroke:#0369a1,stroke-width:2px,color:#0c4a6e
  classDef layerEntry fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a
  classDef layerPipe fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#312e81
  classDef layerApi fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#4c1d95
  classDef layerDomain fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#3b0764
  classDef layerAsync fill:#faf5ff,stroke:#a855f7,stroke-width:2px,color:#581c87
  classDef layerData fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#064e3b
  classDef layerExt fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#7c2d12

  class SPA,ADM layerClient
  class DAPHNE layerEntry
  class HTTP_PIPE,WS_PIPE layerPipe
  class REST,SSE,WS_AI,META layerApi
  class users,courses,homeworks,webinars,applications,carts,payments,core,notifications,ai_chat,admin_panel,stats layerDomain
  class BEAT,WORKER,TASKS layerAsync
  class PG,REDIS,RMQ,S3 layerData
  class AGORA,KINE,YGPT,OAUTH,COMMS layerExt
```

| Слой | Что происходит |
|------|----------------|
| ① Клиенты | SPA ходит в API/SSE/WS; админка — в `/admin/` |
| ② ASGI | `Daphne` маршрутизирует HTTP и WebSocket |
| ③ Конвейер | HTTP: JWT и middleware; WS: проверка токена |
| ④ Интерфейсы | REST, поток уведомлений, чат, служебные URL |
| ⑤ `apps/` | Бизнес-логика и ORM; группы по доменам |
| ⑥ Celery | Beat ставит задачи в RabbitMQ, Worker исполняет |
| ⑦ Данные | PG — источник истины; Redis — кэш и real-time; S3 — файлы |
| ⑧ Интеграции | Видео, записи, ИИ, OAuth, почта и SMS |

**Точка входа** — `project/asgi.py`: HTTP через Django, WebSocket через `project/routing.py` (сейчас — `ai_chat_bot`).

**Конфигурация** — `project/settings.py`, маршруты — `project/urls.py`, Celery — `project/celery.py`.

**Доменные модули** — `apps/<name>/`: модели, `api/` (views, serializers, urls), при необходимости `tasks.py`, `signals.py`, `tests/`.

| Приложение | Назначение |
|------------|------------|
| `users` | Регистрация, JWT, профиль, OAuth |
| `courses` | Курсы, секции, уроки, каталог |
| `webinars` | Эфиры, Agora, записи, Kinescope |
| `homeworks` | Попытки, ответы, проверка |
| `carts` | Корзина |
| `payments` | Платежи |
| `applications` | Заявки на спецкурсы |
| `notifications` | Уведомления, SSE |
| `ai_chat_bot` | ИИ-чат, WebSocket |
| `admin_panel` | API модератора |
| `stats` | Аналитика (`/api/v1/statistics/`) |
| `core` | Медиа-ассеты, health, общие API |

**Кэш Redis** (не CI): `default`, `hot`, `cold` — разные TTL в `CACHES`.

**Периодические задачи** (`CELERY_BEAT_SCHEDULE`): idle-вебинары, опрос S3-событий ассетов, sweep pending/orphaned.

---

## Базы данных

| Хранилище | Когда | Назначение |
|-----------|--------|------------|
| **PostgreSQL** | prod / dev | Основные данные (`DB_*` в `.env`) |
| **SQLite** | `CI=1` или `manage.py test` | Тесты без внешней БД |
| **Redis** | prod / dev | Кэш, Celery results, channel layers |
| **FileBasedCache** | тесты | Замена Redis в CI |
| **S3** | `USE_S3=True` | Медиа и staticfiles |
| **Локальный диск** | `USE_S3=False`, `DEBUG` | `/media/`, `/static/` |

Миграции:

```bash
python manage.py migrate
python manage.py makemigrations <app>
```

---

## Структура каталога

```
backend/
├── apps/              # доменные Django-приложения
├── project/           # settings, urls, asgi, celery, middleware
├── templates/
├── manage.py
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Запуск

**Docker** (из корня монорепы, см. [README](../README.md)):

`docker compose up --build`

**Локально:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

docker compose -f ../docker-compose.yml up redis rabbitmq -d

python manage.py migrate
daphne -b 0.0.0.0 -p 9000 project.asgi:application
```

Celery (отдельные процессы):

```bash
celery -A project worker -l info
celery -A project beat -l info
```

| Endpoint | URL |
|----------|-----|
| API | http://localhost:9000/api/v1/ |
| Swagger | http://localhost:9000/api/v1/swagger |
| OpenAPI schema | http://localhost:9000/api/v1/schema/ |
| Admin | http://localhost:9000/admin/ |
| Health | `/health/live/`, `/health/ready/` |

Авторизация: `Authorization: Bearer <access>`, refresh — `POST /api/v1/auth/token/refresh/`.

---

## Окружение

```bash
cp .env.example .env
```

Ключевые группы переменных: Django (`SECRET_KEY`, `DEBUG`), PostgreSQL, Redis/Celery/RabbitMQ, S3, Agora, Kinescope, Yandex GPT, OAuth, почта/SMS. Полный список — в [.env.example](.env.example).

