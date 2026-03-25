# ──────────────────────────────────────────────
#  Profession Web App — Makefile
# ──────────────────────────────────────────────
#
#  Использование:  make <цель>
#  Справка:        make help
#

# Переменные (можно переопределить при вызове: make up COMPOSE=podman-compose)
COMPOSE    = docker-compose
BACKEND    = $(COMPOSE) exec backend
MANAGE     = $(BACKEND) python3 manage.py
CELERY_SVC = celery_worker

# ─── Основные команды ────────────────────────

.PHONY: help
help: ## Показать список доступных команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── Docker ──────────────────────────────────

.PHONY: build
build: ## Собрать все образы
	$(COMPOSE) build

.PHONY: up
up: ## Запустить все сервисы
	$(COMPOSE) up -d

.PHONY: up-logs
up-logs: ## Запустить все сервисы и показать логи
	$(COMPOSE) up

.PHONY: down
down: ## Остановить все сервисы
	$(COMPOSE) down

.PHONY: restart
restart: ## Перезапустить все сервисы
	$(COMPOSE) restart

.PHONY: rebuild
rebuild: down build up ## Пересобрать и запустить заново

.PHONY: ps
ps: ## Показать статус контейнеров
	$(COMPOSE) ps

.PHONY: logs
logs: ## Логи всех сервисов (follow)
	$(COMPOSE) logs -f

.PHONY: logs-backend
logs-backend: ## Логи только backend
	$(COMPOSE) logs -f backend

.PHONY: logs-celery
logs-celery: ## Логи только Celery worker
	$(COMPOSE) logs -f $(CELERY_SVC)

# ─── Django ──────────────────────────────────

.PHONY: migrate
migrate: ## Применить миграции
	$(MANAGE) migrate --noinput

.PHONY: makemigrations
makemigrations: ## Создать миграции
	$(MANAGE) makemigrations

.PHONY: createsuperuser
createsuperuser: ## Создать суперпользователя
	$(MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic: ## Собрать статику
	$(MANAGE) collectstatic --noinput

.PHONY: shell
shell: ## Django shell
	$(MANAGE) shell

.PHONY: bash
bash: ## Bash внутри контейнера backend
	$(BACKEND) bash

.PHONY: dbshell
dbshell: ## Подключиться к БД через Django
	$(MANAGE) dbshell

# ─── Celery ──────────────────────────────────

.PHONY: celery-restart
celery-restart: ## Перезапустить Celery worker
	$(COMPOSE) restart $(CELERY_SVC)

.PHONY: celery-stop
celery-stop: ## Остановить Celery worker
	$(COMPOSE) stop $(CELERY_SVC)

# ─── Очистка ─────────────────────────────────

.PHONY: clean
clean: ## Остановить контейнеры и удалить volumes
	$(COMPOSE) down -v

.PHONY: prune
prune: ## Удалить неиспользуемые Docker-ресурсы
	docker system prune -f
