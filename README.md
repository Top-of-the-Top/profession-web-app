# Profession Web App

>Курсовая работа Щербакова Артёма Юрьевича, Павлычева Семена Михайловича и Комковой Полины Дмитриевны 
>"Веб-приложение для онлайн-обучения с поддержкой видеосвязи и ИИ-помощника" на втором курсе ПИ ФКН НИУ ВШЭ

Платформа предоставляет инструменты для преподавателей и студентов: курсы с разделами и уроками, видеовебинары с записью и интерактивной доской, домашние задания с автоматической и ручной проверкой, AI-чат на основе материалов курса, расписание занятий и систему уведомлений в реальном времени.

## Контакты для связи

- [aishcherbakov@edu.hse.ru](mailto:aishcherbakov@edu.hse.ru)
- [smpavlyhcev@edu.hse.ru](mailto:smpavlyhcev@edu.hse.ru)
- [pdkomkova@edu.hse.ru](mailto:pdkomkova@edu.hse.ru)

## Наш стек

- **Бэкенд:** Python, Django, Django REST Framework, Django Channels (ASGI / Daphne), Celery, PostgreSQL, Redis
- **Фронтенд:** React, TypeScript, Vite, TanStack Query, Zustand, Zod
- **Инфраструктура:** Docker Compose, Nginx, Kinescope (видеохостинг), Yandex Cloud S3, SSE и WebSocket
- **Интеграции:** OAuth (VK ID, Яндекс ID), e-mail/SMS-уведомления, Agora, Kinescope

## Развёртывание через Docker

### Требования

- Docker 24+
- Docker Compose v2

### Запуск

```bash
git clone https://github.com/Top-of-the-Top/profession-web-app
cd profession-web-app
cp .env.example .env
```

Заполнить `.env` (секреты Django, доступы к S3, ключи OAuth, токены Kinescope и др.), затем:

```bash
docker compose build
docker compose up -d
```

Применить миграции и собрать статику:

```bash
docker compose run --rm --no-deps backend python manage.py migrate --noinput
docker compose run --rm --no-deps backend python manage.py collectstatic --noinput
```



После запуска:

- Фронтенд: `http://localhost:3000`
- Бэкенд / API: `http://localhost:9000/api/v1/`
- Админ-панель Django: `http://localhost:9000/admin/`

### Остановка

```bash
docker compose down
```

## Структура

- `backend/` — Django-проект (REST API, ASGI, Celery, бизнес-логика)
- `frontend/` — SPA на React + Vite
- `docker-compose.yml` — оркестрация сервисов
- `.github/workflows/` — CI/CD (тесты, деплой на staging и prod)

