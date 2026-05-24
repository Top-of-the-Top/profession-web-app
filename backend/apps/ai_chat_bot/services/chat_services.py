import logging

from asgiref.sync import sync_to_async
from django.conf import settings

from apps.ai_chat_bot.models import Chat, Message, Session
from apps.ai_chat_bot.services.base_service import YandexAIBase

logger = logging.getLogger(__name__)


class YandexChatAIService(YandexAIBase):
    session: Session

    async def get_or_create_session(self, user, course):
        logger.info(
            "Establishing connection to new chat session in course %s for user %s",
            course.pk,
            user.pk,
        )
        session, created = await sync_to_async(Session.objects.get_or_create)(
            course=course, user=user
        )
        self.session = session
        if created:
            logger.info("Created new chat session %s", session.session_id)
        return session

    async def get_chats(self):
        logger.info("Getting all chats for session_id=%s", self.session.session_id)
        return await sync_to_async(
            lambda: list(self.session.chats.all().order_by("-updated_at"))
        )()

    async def get_chat_for_current_session(self, chat_id):
        return await sync_to_async(Chat.objects.get)(
            chat_id=chat_id,
            session=self.session,
        )

    async def get_chat_history(self, chat_id):
        chat = await self.get_chat_for_current_session(chat_id)
        logger.info("Getting chat history for chat_id=%s", chat.chat_id)
        return await sync_to_async(
            lambda: list(chat.messages.all().order_by("updated_at"))
        )()

    async def save_message(self, chat, role, content):
        logger.info("Saving message %s", content)
        return await sync_to_async(Message.objects.create)(chat=chat, role=role, content=content)

    async def update_chat_summary(self, chat_id: str, summary: str) -> None:
        await sync_to_async(Chat.objects.filter(chat_id=chat_id).update)(
            context_summary=summary
        )

    async def create_new_chat(self):
        logger.info("Creating new chat for session_id=%s", self.session.session_id)
        chat = await sync_to_async(Chat.objects.create)(session=self.session)
        logger.info("Created new chat_id=%s", chat.chat_id)
        return chat

    async def delete_chat(self, chat_id):
        chat = await self.get_chat_for_current_session(chat_id)
        logger.info("Deleting chat_id=%s", chat.chat_id)
        await sync_to_async(Chat.objects.filter(chat_id=chat.chat_id).delete)()

    async def ask_question_stream(self, text, vs_id: str | None = None, course_title: str | None = None):
        logger.info("Create response stream for session %s", self.session.session_id)
        try:
            async with self._semaphore:
                kwargs = dict(
                    model=settings.YANDEX_MODEL or settings.YANDEX_ASSISTANT_ID,
                    input=text,
                    stream=True,
                )
                if vs_id:
                    kwargs["tools"] = [{"type": "file_search", "vector_store_ids": [vs_id]}]

                course_name = f"«{course_title}»" if course_title else "курса"
                kwargs["instructions"] = (
                    f"Ты ИИ-ассистент образовательного {course_name}. "
                    "Отвечай на русском языке, точно и по делу. "
                    "Используй поиск по материалам курса ТОЛЬКО когда студент задаёт "
                    "содержательный вопрос о темах, уроках или понятиях курса. "
                    "Приветствия, благодарности и общие фразы — обрабатывай без поиска."
                )

                response_stream = await self.client.responses.create(**kwargs)
                async for event in response_stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta

        except Exception as e:
            logger.error("Error while creating a new response stream: %s", e)
            raise
