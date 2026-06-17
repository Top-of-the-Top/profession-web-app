<div align="center">

# Profession Web App — Бэкенд

**Django 6 ASGI-сервер платформы онлайн-обучения**

REST API · WebSocket-чат с ИИ · уведомления в реальном времени · фоновые задачи

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,django,postgresql,redis,rabbitmq,docker&theme=dark" alt="Backend Stack" />
</p>

**Ядро**<br/>
<p align="center">
  <img src="https://img.shields.io/badge/DRF-A30000?style=flat-square&logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/Daphne-ASGI-092E20?style=flat-square&logo=django&logoColor=white" alt="Daphne" />
  <img src="https://img.shields.io/badge/Channels-WebSocket-092E20?style=flat-square&logo=django&logoColor=white" alt="Channels" />
  <img src="https://img.shields.io/badge/drf--spectacular-OpenAPI-6BA539?style=flat-square&logo=openapiinitiative&logoColor=white" alt="OpenAPI" />
</p>

**Очереди и задачи**<br/>
<p align="center">
  <img src="https://img.shields.io/badge/Celery-Beat-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/Flower-monitoring-37814A?style=flat-square&logo=celery&logoColor=white" alt="Flower" />
</p>

**Данные и хранилище**<br/>
<p align="center">
  <img src="https://img.shields.io/badge/S3-django--storages-5282FF?style=flat-square&logo=yandexcloud&logoColor=white" alt="S3" />
</p>

**Аутентификация и ИИ**<br/>
<p align="center">
  <img src="https://img.shields.io/badge/SimpleJWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white" alt="JWT" />
  <img src="https://img.shields.io/badge/VK%20ID-0077FF?style=flat-square&logo=vk&logoColor=white" alt="VK ID" />
  <img src="https://img.shields.io/badge/Яндекс%20ID-FC3F1D?style=flat-square&logo=yandex&logoColor=white" alt="Яндекс ID" />
  <img src="https://img.shields.io/badge/Yandex%20GPT-Vector%20Store-5282FF?style=flat-square&logo=yandex&logoColor=white" alt="Yandex GPT" />
  <img src="https://img.shields.io/badge/Unfold-admin-1F2937?style=flat-square&logo=django&logoColor=white" alt="Unfold" />
</p>

</div>

> Серверная часть платформы «Profession». Корневой README и Docker Compose — в [корне монорепы](../README.md), клиентская часть — в [frontend/README.md](../frontend/README.md).

---

## Содержание

- [Архитектура](#архитектура)
- [Доменные модули](#доменные-модули)
- [Доменная модель данных](#доменная-модель-данных)
- [Подсистема ИИ-ассистента](#подсистема-ии-ассистента)
- [Подсистема уведомлений](#подсистема-уведомлений)
- [Хранилища данных](#хранилища-данных)
- [API и аутентификация](#api-и-аутентификация)
- [Фоновые задачи](#фоновые-задачи)
- [Запуск](#запуск)
- [Тестирование](#тестирование)
- [Окружение](#окружение)

---

## Архитектура

Единая точка входа — `project/asgi.py`: HTTP-запросы идут через Django, WebSocket — через `project/routing.py`. Бизнес-логика разнесена по доменным приложениям в `apps/`, тяжёлая и периодическая работа — в Celery.

```mermaid
flowchart TB
  subgraph L1["1 · Клиенты"]
    direction LR
    SPA["React SPA"]
    ADM["Django Admin · Unfold"]
  end

  subgraph L2["2 · Точка входа · project/asgi.py"]
    DAPHNE["Daphne ASGI<br/>ProtocolTypeRouter"]
  end

  subgraph L3["3 · Конвейер запросов"]
    direction LR
    HTTP_PIPE["HTTP<br/>Security · CORS · Session<br/>JWT · Timing · Orbit"]
    WS_PIPE["WebSocket<br/>JWT Auth Middleware"]
  end

  subgraph L4["4 · Публичные интерфейсы"]
    direction TB
    REST["REST API · /api/v1/ · OpenAPI"]
    SSE["Server-Sent Events · уведомления"]
    WS_AI["WebSocket · ai_chat_bot"]
    META["Health · Swagger · /admin/"]
  end

  subgraph L5["5 · Доменный слой · apps/"]
    direction LR
    users["users"]
    courses["courses"]
    homeworks["homeworks"]
    webinars["webinars"]
    carts["carts"]
    payments["payments"]
    notifications["notifications"]
    ai_chat["ai_chat_bot"]
    core["core"]
    stats["stats"]
  end

  subgraph L6["6 · Фоновая обработка"]
    direction LR
    BEAT["Celery Beat"]
    WORKER["Celery Worker"]
  end

  subgraph L7["7 · Персистентность"]
    direction LR
    PG[("PostgreSQL")]
    REDIS[("Redis<br/>cache · channels")]
    RMQ["RabbitMQ"]
    S3[("S3")]
  end

  subgraph L8["8 · Внешние интеграции"]
    direction LR
    AGORA["Agora"]
    KINE["Kinescope"]
    YGPT["Yandex GPT"]
    OAUTH["OAuth · Яндекс · VK"]
    COMMS["SMTP · SMS"]
  end

  SPA --> DAPHNE
  ADM --> DAPHNE
  DAPHNE --> HTTP_PIPE & WS_PIPE
  HTTP_PIPE --> REST & SSE & META
  WS_PIPE --> WS_AI
  REST --> L5
  SSE --> notifications
  WS_AI --> ai_chat

  L5 --> PG
  courses --> REDIS
  core --> S3
  webinars --> S3 & AGORA & KINE
  ai_chat --> YGPT
  users --> OAUTH & COMMS
  notifications --> COMMS

  REST -.->|события| RMQ
  notifications -.->|publish| RMQ
  BEAT -->|cron| RMQ --> WORKER
  WORKER --> PG & S3 & KINE & REDIS

  classDef client fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
  classDef entry fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef pipe fill:#e0e7ff,stroke:#4f46e5,color:#312e81
  classDef api fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
  classDef domain fill:#f5f3ff,stroke:#8b5cf6,color:#3b0764
  classDef async fill:#faf5ff,stroke:#a855f7,color:#581c87
  classDef data fill:#d1fae5,stroke:#059669,color:#064e3b
  classDef ext fill:#ffedd5,stroke:#ea580c,color:#7c2d12
  class SPA,ADM client
  class DAPHNE entry
  class HTTP_PIPE,WS_PIPE pipe
  class REST,SSE,WS_AI,META api
  class users,courses,homeworks,webinars,carts,payments,notifications,ai_chat,core,stats domain
  class BEAT,WORKER async
  class PG,REDIS,RMQ,S3 data
  class AGORA,KINE,YGPT,OAUTH,COMMS ext
```

**Конфигурация** — `project/settings.py` · **маршруты** — `project/urls.py` · **Celery** — `project/celery.py`. Каждый домен `apps/<name>/` содержит модели, `api/` (views, serializers, urls) и при необходимости `tasks.py`, `signals.py`, `services/`, `tests/`.

---

## Доменные модули

Двенадцать приложений сгруппированы по зонам ответственности:

```mermaid
mindmap
  root((apps/))
    Доступ
      users · JWT · OAuth · профиль
    Обучение
      courses · секции · уроки
      homeworks · попытки · проверка
      webinars · Agora · Kinescope
      applications · заявки
    Коммерция
      carts · корзина
      payments · платежи
    Платформа
      core · медиа-ассеты · health
      notifications · SSE · рассылки
      ai_chat_bot · WebSocket · ИИ
      admin_panel · API модератора
      stats · аналитика
```

---

## Доменная модель данных

Ядро предметной области — иерархия учебного контента и попыток сдачи ДЗ. Курс ведёт один или несколько авторов (M2M), внутри — секции, уроки, задания; студент сдаёт попытку, которая разбивается на ответы и ручные ревью.

```mermaid
erDiagram
  USER }o--o{ COURSE : "авторство (M2M)"
  COURSE ||--o{ SECTION : "содержит"
  SECTION ||--o{ LESSON : "содержит"
  LESSON ||--o{ HOMEWORK : "содержит"
  HOMEWORK ||--o{ QUESTION : "тест-вопросы"
  HOMEWORK ||--o{ TASK : "задания"
  USER ||--o{ ATTEMPT : "сдаёт"
  HOMEWORK ||--o{ ATTEMPT : "попытки"
  ATTEMPT ||--o{ QUESTIONANSWER : "ответы"
  ATTEMPT ||--o{ TASKANSWER : "решения"
  TASKANSWER ||--o| TASKREVIEW : "ручная проверка"

  USER {
    uuid id PK
    string role "student / teacher / moderator"
    bytes email_cipher "шифрованный e-mail"
  }
  COURSE {
    uuid course_id PK
    string title
    string slug
    int price
    string yandex_vs_id "ИИ Vector Store"
  }
  SECTION {
    int section_number
    string title
  }
  LESSON {
    int lesson_number
    string title
    json content "BlockNote"
  }
  ATTEMPT {
    datetime created_at
    user reviewed_by "проверяющий"
  }
```

Параллельная ветка — диалоги с ИИ-ассистентом: одна `Session` на пару «пользователь + курс», внутри независимые чаты с историей и сжатым контекстом.

```mermaid
erDiagram
  USER ||--o{ SESSION : ""
  COURSE ||--o{ SESSION : ""
  SESSION ||--o{ CHAT : ""
  CHAT ||--o{ MESSAGE : ""
  SESSION {
    uuid id PK
  }
  CHAT {
    uuid id PK
    string title "автозаголовок"
    text context_summary "сжатый контекст"
  }
  MESSAGE {
    uuid id PK
    string role "user / assistant"
    text content
  }
```

---

## Подсистема ИИ-ассистента

`ai_chat_bot` — ИИ-помощник, отвечающий по материалам конкретного курса. Соединение — WebSocket (`?token=JWT` в query-параметре, т.к. браузер не шлёт заголовки при апгрейде), ответы приходят стримингом по токену.

```mermaid
sequenceDiagram
  participant U as Клиент
  participant C as AiChatConsumer
  participant DB as PostgreSQL
  participant VS as Yandex Vector Store
  participant G as Yandex GPT
  U->>C: send message
  C->>DB: сохранить вопрос
  C-->>U: starting answer
  opt у курса есть Vector Store
    C->>VS: file_search по материалам
    C-->>U: searching context
  end
  loop генерация
    G-->>C: chunk
    C-->>U: streaming response
  end
  C-->>U: finishing answer
```

**Модели** — `Session (user + course) → Chat → Message`. **Vector Store** строится из материалов курса (overview + по файлу на урок) и пересобирается при изменении контента; при его отсутствии бот работает в режиме graceful degradation — отвечает по истории диалога. Длинные диалоги сжимаются компрессором контекста (TextRank), summary хранится в БД для восстановления после переподключения.

---

## Подсистема уведомлений

Доменные события проходят через `NotificationDispatcher`, который по типу события вызывает обработчики: запись в БД + публикация в RabbitMQ (для SSE) и, опционально, отправка e-mail/SMS.

```mermaid
flowchart LR
  EV["Событие<br/>view · signal · task"] --> D{NotificationDispatcher}
  D -->|SSE| T1["Celery task"]
  T1 --> N[("Notification<br/>PostgreSQL")]
  T1 --> R["RabbitMQ<br/>topic exchange"]
  R -->|user.id · course.id · system.all| STREAM["SSE-поток<br/>StreamingHttpResponse"]
  STREAM --> CLIENT["Клиент · EventSource"]
  D -->|with_email| T2["Celery task"]
  T2 -->|decrypt email| SMTP["SMTP / SMS"]

  classDef a fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
  classDef d fill:#d1fae5,stroke:#059669,color:#064e3b
  classDef x fill:#ffedd5,stroke:#ea580c,color:#7c2d12
  class EV,D,T1,T2 a
  class N,R,STREAM d
  class SMTP,CLIENT x
```

Уведомления бывают трёх типов: **личные** (конкретному пользователю), **курсовые** (всем записавшимся на курс) и **системные** (всем). Клиент держит один SSE-канал и подписывается на свои routing keys; при разрыве переподключается сам. E-mail отправляется параллельно SSE, если событие помечено `with_email`; адрес хранится в зашифрованном виде и расшифровывается перед отправкой.

---

## Хранилища данных

```mermaid
flowchart LR
  APP["Django · Celery"]
  APP --> PG[("PostgreSQL<br/>источник истины")]
  APP --> REDIS[("Redis<br/>cache: default · hot · cold<br/>channels · Celery results")]
  APP --> RMQ["RabbitMQ<br/>брокер · события"]
  APP --> S3[("S3 · Yandex<br/>media · static")]

  classDef d fill:#d1fae5,stroke:#059669,color:#064e3b
  classDef a fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
  class PG,REDIS,RMQ,S3 d
  class APP a
```

В CI и тестах (`CI=1` или `manage.py test`) внешние зависимости подменяются: PostgreSQL → SQLite, Redis-кэш → `FileBasedCache`, брокер Celery → in-memory с `TASK_ALWAYS_EAGER`. Это позволяет прогонять тесты без поднятого окружения.

---

## API и аутентификация

Все ресурсы — под префиксом `/api/v1/` (модерация, статистика — `/api/v1/statistics/`). Аутентификация — JWT: `Authorization: Bearer <access>`.

| Endpoint | Назначение |
|----------|------------|
| `/api/v1/` | REST-ресурсы доменных приложений |
| `/api/v1/auth/token/refresh/` | Обновление access-токена |
| `/api/v1/swagger` · `/api/v1/schema/` | Swagger UI · OpenAPI-схема |
| `/admin/` | Админ-панель (Unfold) |
| `/health/live/` · `/health/ready/` | Liveness · readiness пробы |

Access-токен живёт 15 минут, refresh — 7 дней с ротацией (`SIMPLE_JWT`). Роли пользователя: **student**, **teacher**, **moderator**.

---

## Фоновые задачи

Celery Beat ставит периодические задачи в RabbitMQ, Worker их исполняет:

```
check-idle-webinars        каждые 60с    — закрытие «зависших» эфиров
assets-poll-s3-events      каждые 30с    — обработка событий загрузки в S3
assets-sweep-pending       каждые 10мин  — очистка незавершённых ассетов
assets-sweep-orphaned      каждый час    — удаление осиротевших файлов
```

Мониторинг задач — **Flower** (`http://localhost:15666`).

---

## Запуск

**Через Docker** (рекомендуется) — из корня монорепы, см. [README](../README.md):

```bash
docker compose up --build
```

**Локально:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# поднять инфраструктуру
docker compose -f ../docker-compose.yml up redis rabbitmq -d

python manage.py migrate
daphne -b 0.0.0.0 -p 9000 project.asgi:application
```

Celery — отдельными процессами:

```bash
celery -A project worker -l info
celery -A project beat -l info
```

После запуска: API — http://localhost:9000/api/v1/ · Swagger — `/api/v1/swagger` · Admin — `/admin/`.

---

## Тестирование

```bash
# все тесты приложения (SQLite, eager Celery)
CI=1 python manage.py test apps

# конкретное приложение
python manage.py test apps.notifications -v 2
```

Из корня доступны обёртки `make test` (с параметром `APP=apps.<name>`) и сценарные цели вроде `make test-notifications-pipeline`. В CI тесты прогоняются на каждый PR (`.github/workflows/backend-tests.yml`), миграции проверяются отдельным workflow.

---

## Окружение

Конфигурация — через `.env` (см. [`.env.example`](.env.example)):

```mermaid
flowchart LR
  ENV[".env"] --- DJ["Django<br/>SECRET_KEY · DEBUG · hosts"]
  ENV --- DB["PostgreSQL<br/>DB_*"]
  ENV --- Q["Redis · Celery · RabbitMQ"]
  ENV --- ST["S3<br/>USE_S3 · AWS_*"]
  ENV --- INT["Интеграции<br/>Agora · Kinescope · Yandex GPT"]
  ENV --- AU["OAuth · SMTP · SMS"]

  classDef e fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef g fill:#f5f3ff,stroke:#8b5cf6,color:#3b0764
  class ENV e
  class DJ,DB,Q,ST,INT,AU g
```

Полный список переменных с пояснениями — в [`.env.example`](.env.example).
