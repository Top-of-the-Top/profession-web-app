<div align="center">

# Profession Web App

**Образовательная платформа для онлайн-обучения с видеосвязью и ИИ-помощником**

Курсы и уроки · живые вебинары с интерактивной доской · домашние задания с проверкой · ИИ-ассистент по материалам курса · уведомления в реальном времени

**Backend**<br/>
<p align="center">
  <img src="https://skillicons.dev/icons?i=python,django&theme=dark" alt="Backend" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/DRF-A30000?style=flat-square&logo=django&logoColor=white" alt="DRF" />
  <img src="https://img.shields.io/badge/Channels-ASGI%20%2F%20Daphne-092E20?style=flat-square&logo=django&logoColor=white" alt="Channels" />
  <img src="https://img.shields.io/badge/Celery-Beat-37814A?style=flat-square&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/SimpleJWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white" alt="JWT" />
</p>

**Frontend**<br/>
<p align="center">
  <img src="https://skillicons.dev/icons?i=react,typescript,vite,tailwindcss&theme=dark" alt="Frontend" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/TanStack%20Query-FF4154?style=flat-square&logo=reactquery&logoColor=white" alt="TanStack Query" />
  <img src="https://img.shields.io/badge/Zustand-443E38?style=flat-square&logo=react&logoColor=white" alt="Zustand" />
  <img src="https://img.shields.io/badge/Zod-3E67B1?style=flat-square&logo=zod&logoColor=white" alt="Zod" />
</p>

**Infra**<br/>
<p align="center">
  <img src="https://skillicons.dev/icons?i=docker,nginx,postgresql,redis,rabbitmq,githubactions&theme=dark" alt="Infra" />
</p>
<p align="center">
  <img src="https://img.shields.io/badge/S3-Yandex%20Cloud-5282FF?style=flat-square&logo=yandexcloud&logoColor=white" alt="S3" />
</p>

**Интеграции**<br/>
<p align="center">
  <img src="https://img.shields.io/badge/Yandex%20GPT-AI-5282FF?style=flat-square&logo=yandex&logoColor=white" alt="Yandex GPT" />
  <img src="https://img.shields.io/badge/Agora-RTC%20%2F%20Whiteboard-099DFD?style=flat-square&logo=agora&logoColor=white" alt="Agora" />
  <img src="https://img.shields.io/badge/Kinescope-video-6C5CE7?style=flat-square" alt="Kinescope" />
  <img src="https://img.shields.io/badge/VK%20ID-0077FF?style=flat-square&logo=vk&logoColor=white" alt="VK ID" />
  <img src="https://img.shields.io/badge/Яндекс%20ID-FC3F1D?style=flat-square&logo=yandex&logoColor=white" alt="Яндекс ID" />
</p>

</div>

---

> Курсовая работа студентов 2 курса ОП «Программная инженерия» ФКН НИУ ВШЭ
> **Щербакова Артёма Юрьевича · Павлычева Семёна Михайловича · Комковой Полины Дмитриевны**
> на тему «Веб-приложение для онлайн-обучения с поддержкой видеосвязи и ИИ-помощника».

**Profession** — полноценная LMS-платформа: преподаватель собирает курс из секций и уроков, проводит живые вебинары с записью и совместной доской, выдаёт домашние задания и проверяет их, а студент учится, задаёт вопросы ИИ-ассистенту, который отвечает по материалам конкретного курса, и получает уведомления о дедлайнах и оценках в реальном времени.

## Содержание

- [Ключевые возможности](#ключевые-возможности)
- [Архитектура системы](#архитектура-системы)
- [Структура монорепозитория](#структура-монорепозитория)
- [Быстрый старт](#быстрый-старт)
- [Сервисы и порты](#сервисы-и-порты)
- [Команды разработки](#команды-разработки)
- [CI/CD и окружения](#cicd-и-окружения)
- [Документация](#документация)
- [Команда](#команда)

---

## Ключевые возможности

| Домен | Возможности |
|-------|-------------|
| **Обучение** | Каталог курсов, иерархия «курс → секция → урок», уроки в формате блочного редактора, превью и публикация |
| **Вебинары** | Живые трансляции (Agora RTC), интерактивная доска (Netless / Fastboard), запись и хостинг на Kinescope |
| **Домашние задания** | Создание заданий, попытки студентов, ручная и автоматическая проверка, оценки и комментарии |
| **ИИ-ассистент** | Чат по материалам курса на Yandex GPT с семантическим поиском (Vector Store), стриминг ответов через WebSocket |
| **Уведомления** | Реальное время через Server-Sent Events + RabbitMQ, дублирование на e-mail/SMS, напоминания о дедлайнах |
| **Расписание** | Календарь занятий и вебинаров, заявки на спецкурсы |
| **Коммерция** | Корзина и оформление покупки курсов, платежи |
| **Аналитика** | Статистика по студентам и курсам, карточки успеваемости |
| **Роли и доступ** | Разграничение прав: **студент**, **преподаватель**, **модератор** (RBAC на бэкенде и фронтенде) |
| **Аутентификация** | JWT, OAuth через **VK ID** и **Яндекс ID**, подтверждение по SMS/e-mail |

---

## Архитектура системы

Монорепозиторий из двух приложений (SPA + API), оркестрируемых через Docker Compose. Бэкенд работает на ASGI (Daphne) и обслуживает REST, WebSocket и SSE одновременно; тяжёлая и периодическая работа вынесена в Celery.

```mermaid
flowchart LR
  subgraph CLIENT["Клиент"]
    SPA["React SPA<br/>Vite · FSD"]
  end

  subgraph EDGE["Edge"]
    NGINX["Nginx<br/>static + reverse proxy"]
  end

  subgraph APP["Приложение"]
    direction TB
    API["Django + DRF<br/>Daphne ASGI"]
    WS["WebSocket<br/>Django Channels"]
    SSE["SSE-поток<br/>уведомления"]
    WORKER["Celery Worker + Beat<br/>фоновые задачи"]
  end

  subgraph DATA["Данные"]
    direction TB
    PG[("PostgreSQL")]
    REDIS[("Redis<br/>cache · channels")]
    RMQ["RabbitMQ<br/>broker · events"]
    S3[("S3<br/>Yandex Object Storage")]
  end

  subgraph EXT["Внешние сервисы"]
    direction TB
    AGORA["Agora<br/>RTC · доска"]
    KINE["Kinescope<br/>видеохостинг"]
    YGPT["Yandex GPT<br/>ИИ · Vector Store"]
    OAUTH["VK ID · Яндекс ID"]
    COMMS["SMTP · SMS"]
  end

  SPA --> NGINX --> API
  SPA -. WebSocket .-> WS
  SPA -. EventSource .-> SSE

  API --> PG & REDIS & S3
  WS --> REDIS & YGPT
  SSE --> RMQ
  API -- события --> RMQ --> WORKER
  WORKER --> PG & S3 & KINE & REDIS

  API --> OAUTH & COMMS
  API --> AGORA & KINE

  classDef c fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
  classDef e fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef a fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
  classDef d fill:#d1fae5,stroke:#059669,color:#064e3b
  classDef x fill:#ffedd5,stroke:#ea580c,color:#7c2d12
  class SPA c
  class NGINX e
  class API,WS,SSE,WORKER a
  class PG,REDIS,RMQ,S3 d
  class AGORA,KINE,YGPT,OAUTH,COMMS x
```

| Слой | Технология | Ответственность |
|------|------------|-----------------|
| Клиент | React SPA | UI, маршрутизация, состояние, real-time клиенты |
| Edge | Nginx | Раздача статики, проксирование `/api`, gzip, security-заголовки |
| API / WS / SSE | Django (Daphne ASGI) | REST, WebSocket-чат, SSE-уведомления, бизнес-логика |
| Очереди | Celery + Beat | Синхронизация Vector Store, обработка вебинаров, рассылки, периодические задачи |
| Данные | PostgreSQL · Redis · RabbitMQ · S3 | Источник истины · кэш и real-time · брокер · файлы |
| Внешние | Agora · Kinescope · Yandex GPT · OAuth · SMTP/SMS | Видео, записи, ИИ, авторизация, коммуникации |

> Детальные схемы — в [README бэкенда](backend/README.md) и [README фронтенда](frontend/README.md).

---

## Структура монорепозитория

```
profession-web-app/
├── backend/                  # Django-проект: REST API, ASGI, Celery, бизнес-логика
│   ├── apps/                 # доменные приложения (users, courses, webinars, ...)
│   ├── project/              # settings, urls, asgi, celery, middleware
│   └── README.md             # ← архитектура и запуск бэкенда
├── frontend/                 # SPA на React + Vite (Feature-Sliced Design)
│   ├── src/                  # app · pages · widgets · features · entities · shared
│   ├── nginx.conf            # конфиг раздачи и проксирования в проде
│   └── README.md             # ← архитектура и запуск фронтенда
├── infra/                    # инфраструктурные артефакты
├── .github/workflows/        # CI/CD: тесты, проверки имён, деплой, релизы
├── docker-compose.yml        # оркестрация всех сервисов
├── docker-compose.override.dev.yml  # dev-режим (HMR фронтенда)
└── Makefile                  # команды разработки
```

---

## Быстрый старт

### Требования

- **Docker 24+** и **Docker Compose v2**

### Запуск через Docker

```bash
git clone https://github.com/Top-of-the-Top/profession-web-app
cd profession-web-app

# Конфигурация бэкенда (секреты Django, доступы к S3, ключи OAuth, токены Kinescope/Agora/Yandex GPT)
cp backend/.env.example backend/.env

# Сборка и запуск всего стека
docker compose build
docker compose up -d
```

Применить миграции и собрать статику:

```bash
docker compose run --rm --no-deps backend python manage.py migrate --noinput
docker compose run --rm --no-deps backend python manage.py collectstatic --noinput
```

Создать суперпользователя для доступа в админку:

```bash
docker compose exec backend python manage.py createsuperuser
```

### Dev-режим (горячая перезагрузка фронтенда)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.dev.yml --profile prod up
```

Остановить всё:

```bash
docker compose down
```

---

## Сервисы и порты

| Сервис | URL / порт | Назначение |
|--------|-----------|------------|
| Фронтенд (SPA) | http://localhost:3000 | Пользовательский интерфейс |
| Бэкенд / API | http://localhost:9000/api/v1/ | REST API |
| Swagger UI | http://localhost:9000/api/v1/swagger | Интерактивная документация API |
| Django Admin | http://localhost:9000/admin/ | Админ-панель (Unfold) |
| RabbitMQ UI | http://localhost:15672 | Управление брокером (`guest`/`guest`) |
| Flower | http://localhost:15666 | Мониторинг Celery-задач |
| PostgreSQL | `localhost:5432` | База данных |
| Redis | `localhost:6379` | Кэш, channels, результаты Celery |

---

## Команды разработки

В корне есть `Makefile` с обёртками над Docker Compose. Несколько полезных целей:

```bash
make help            # список всех команд
make up              # поднять весь стек в фоне
make up-logs         # поднять стек с выводом логов
make down            # остановить
make rebuild         # пересобрать и перезапустить
make migrate         # применить миграции
make makemigrations  # создать миграции
make createsuperuser # создать суперпользователя
make shell           # Django shell
make test            # тесты бэкенда (APP=apps.courses — конкретное приложение)
make logs-backend    # логи бэкенда
make logs-celery     # логи Celery worker
make clean           # остановить и удалить volumes
```

---

## CI/CD и окружения

Автоматизация на **GitHub Actions** (`.github/workflows/`) — от проверки имени ветки до инкрементального деплоя:

```mermaid
flowchart LR
  PR["Pull Request"] --> CHECKS["Проверки<br/>branch · commit · tests · migrations"]
  CHECKS -->|merge| TESTING["deploy-to-testing<br/>professionkid-testing.ru"]
  TESTING --> REL["create-release<br/>тег + changelog"]
  REL --> PROD["deploy-release<br/>professionkid.ru"]

  classDef pr fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
  classDef ci fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
  classDef test fill:#fef9c3,stroke:#ca8a04,color:#713f12
  classDef prod fill:#d1fae5,stroke:#059669,color:#064e3b
  class PR pr
  class CHECKS ci
  class TESTING test
  class REL ci
  class PROD prod
```

| Workflow | Триггер | Что делает |
|----------|---------|------------|
| `backend-tests` | PR в `develop` | Прогон тестов приложений бэкенда (`CI=1`, SQLite) |
| `migration-tests` | PR | Проверка корректности и обратимости миграций |
| `branch-name-check` | push / PR | Валидация имени ветки (`feature/backend/KAN-123-…`) |
| `commit-name-check` | push / PR | Валидация формата сообщений коммитов |
| `deploy-to-testing` | merge | Деплой на **testing**-сервер с детекцией изменений (build только нужных сервисов) |
| `create-release` | вручную | Создание тега и GitHub Release с changelog |
| `deploy-release` | вручную | Деплой выбранного релиза на боевой сервер |

Деплой инкрементальный: через `paths-filter` пересобираются только изменившиеся образы (backend / frontend), миграции запускаются лишь при изменениях в `migrations/`.

| Окружение | Хост | Назначение |
|-----------|------|------------|
| **Testing** | [professionkid-testing.ru](https://professionkid-testing.ru) | Предпродакшен-проверка |
| **Production** | [professionkid.ru](https://professionkid.ru) | Боевая среда |

---

## Документация

| Документ | Описание |
|----------|----------|
| [backend/README.md](backend/README.md) | Архитектура серверной части, домены, запуск, окружение |
| [frontend/README.md](frontend/README.md) | Архитектура SPA (FSD), слои, real-time, запуск |
| `http://localhost:9000/api/v1/swagger` | Интерактивная OpenAPI-документация API |

---

## Команда

| Участник | Контакт |
|----------|---------|
| **Щербаков Артём Юрьевич** | [aishcherbakov@edu.hse.ru](mailto:aishcherbakov@edu.hse.ru) |
| **Павлычев Семён Михайлович** | [smpavlyhcev@edu.hse.ru](mailto:smpavlyhcev@edu.hse.ru) |
| **Комкова Полина Дмитриевна** | [pdkomkova@edu.hse.ru](mailto:pdkomkova@edu.hse.ru) |

<div align="center">

---

ОП «Программная инженерия» · ФКН НИУ ВШЭ · 2026

</div>
