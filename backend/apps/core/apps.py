from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Общие сервисы"

    def ready(self):
        from .meta_management import signals  # noqa: F401
