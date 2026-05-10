from django.apps import AppConfig


class AiChatBotConfig(AppConfig):
    name = "apps.ai_chat_bot"
    verbose_name = "ИИ Ассистент и Чат"

    def ready(self):
        import apps.ai_chat_bot.signals  # noqa: F401
