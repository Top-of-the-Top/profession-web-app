COMPOSE    = docker compose
BACKEND    = $(COMPOSE) exec backend
MANAGE     = $(BACKEND) python3 manage.py
CELERY_SVC = celery_worker
APP        ?=
DIR        ?= apps
ARGS       ?=
VERBOSITY  ?=

ifneq ($(APP),)
ifeq ($(filter apps.%,$(APP)),$(APP))
DJANGO_TEST_LABEL := $(APP)
else
DJANGO_TEST_LABEL := apps.$(APP)
endif
endif

.PHONY: help
help: ## Показать список доступных команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'


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

.PHONY: migrate
migrate: ## Применить миграции
	$(MANAGE) migrate --noinput

.PHONY: makemigrations
makemigrations: ## Создать миграции
	$(MANAGE) makemigrations

.PHONY: startapp
startapp: ## Создать новое Django app
	@if [ -z "$(APP)" ]; then echo "Usage: make startapp APP=<app_name> [DIR=apps]"; exit 1; fi
	$(MANAGE) startapp $(APP) $(DIR)/$(APP)

.PHONY: createsuperuser
createsuperuser: ## Создать суперпользователя
	$(MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic: ## Собрать статику
	$(MANAGE) collectstatic --noinput

.PHONY: shell
shell: ## Django shell
	$(MANAGE) shell

.PHONY: test
test: ## Тесты: make test; APP=apps.notifications; ARGS — ARGS='-v 2'; см. test-notifications-pipeline, test-homework-review-notifications
	$(MANAGE) test $(APP) $(ARGS)

.PHONY: test-app
test-app: ## То же, что make test APP=… (оставлено для привычки)
	@if [ -z "$(APP)" ]; then echo "Usage: make test APP=apps.<имя>   или   make test-app APP=apps.<имя>"; exit 1; fi
	$(MANAGE) test $(APP) $(ARGS)

.PHONY: test-homework-review-notifications test-homeworks-e2e
test-homework-review-notifications: ## ДЗ: ревью → почта + payload для SSE + Notification в БД
	$(MANAGE) test apps.homeworks.tests.test_homework_review_student_notification_pipeline.HomeworkReviewStudentNotificationPipelineTests.test_review_triggers_student_notifications \
		$(if $(strip $(VERBOSITY)),-v $(VERBOSITY)) $(ARGS)

test-homeworks-e2e: ## Алиас make test-homework-review-notifications
	$(MANAGE) test apps.homeworks.tests.test_homework_review_student_notification_pipeline.HomeworkReviewStudentNotificationPipelineTests.test_review_triggers_student_notifications \
		$(if $(strip $(VERBOSITY)),-v $(VERBOSITY)) $(ARGS)

.PHONY: test-notifications-pipeline
test-notifications-pipeline: ## Уведомления: событие проверки ДЗ → БД + почта + перехват publish_event (сквозной)
	$(MANAGE) test apps.notifications.tests.test_homework_reviewed_dispatch_pipeline.HomeworkReviewedDispatchPipelineTests.test_dispatch_homework_reviewed_personal_mail_and_publish_payload \
		$(if $(strip $(VERBOSITY)),-v $(VERBOSITY)) $(ARGS)

.PHONY: bash
bash: ## Bash внутри контейнера backend
	$(BACKEND) bash

.PHONY: dbshell
dbshell: ## Подключиться к БД через Django
	$(MANAGE) dbshell


.PHONY: celery-restart
celery-restart: ## Перезапустить Celery worker
	$(COMPOSE) restart $(CELERY_SVC)

.PHONY: celery-stop
celery-stop: ## Остановить Celery worker
	$(COMPOSE) stop $(CELERY_SVC)


.PHONY: clean
clean: ## Остановить контейнеры и удалить volumes
	$(COMPOSE) down -v

.PHONY: prune
prune: ## Удалить неиспользуемые Docker-ресурсы
	docker system prune -f
