import openai
import asyncio
from django.conf import settings
from apps.courses.models import Course
from apps.ai_chat_bot.models import ChatMessage, ChatSession

class YandexAIBase:
    _semaphore = asyncio.Semaphore(20) # Семафор нужен, чтобы избежать ошибки, когда у нас оч много запросов с 1ого IPшника.

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=settings.YANDEX_API_KEY,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=settings.YANDEX_FOLDER_ID,
        )