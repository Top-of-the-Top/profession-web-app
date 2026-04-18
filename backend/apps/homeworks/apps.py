from django.apps import AppConfig


class HomeworksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.homeworks'
    verbose_name = 'Домашние задания'

    def ready(self):
        from . import signals  # noqa
