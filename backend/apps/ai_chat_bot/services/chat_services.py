
import logging
from django.conf import settings
from apps.ai_chat_bot.models import Message, Session, Chat
from asgiref.sync import sync_to_async
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

        session, created = await sync_to_async(
            Session.objects.get_or_create)(
                course=course,
                user=user
            )
        self.session = session
        
        if created:
            logger.info("Created new chat session %s", session.session_id)

        return session
    
    async def save_message(self, chat,  role, content):
        logger.info("Saving message %s", content)
        return await sync_to_async(Message.objects.create)(
            chat=chat,
            role=role,
            content=content
        )
    
    async def ask_question_stream(self, text):
        logger.info("Create response stream for session %s", self.session.session_id)
        try:
            async with self._semaphore:
                response_stream = await self.client.responses.create(
                    model=settings.YANDEX_MODEL or settings.YANDEX_ASSISTANT_ID,
                    input=text,
                    stream=True,
                )

                async for event in response_stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
        
        except Exception as e:
            logger.error(f"Error while creating a new response stream: {e}")
            raise 

    async def get_chats(self):
        logger.info("Getting all chats for session_id=%s", self.session.session_id)
        get_chats_for_session = lambda x: list(x.chats.all().order_by('-updated_at'))
        chats = await sync_to_async(get_chats_for_session)(self.session)
        return chats

    async def _get_chat_for_current_session(self, chat_id):
        return await sync_to_async(Chat.objects.get)(
            chat_id=chat_id,
            session=self.session,
        )

    async def get_chat_for_current_session(self, chat_id):
        return await self._get_chat_for_current_session(chat_id)

    async def get_chat_history(self, chat_id):
        chat = await self._get_chat_for_current_session(chat_id)
        logger.info("Getting chat history for chat_id=%s", chat.chat_id)
        get_chat_messages = lambda x: list(
            x.messages.filter(is_deleted=False).order_by('-updated_at')
        )
        messages = await sync_to_async(get_chat_messages)(chat)
        return messages
    
    async def delete_chat(self, chat_id):
        chat = await self._get_chat_for_current_session(chat_id)
        logger.info("Deleting chat_id=%s", chat.chat_id)
        del_chat = lambda x: Chat.objects.filter(chat_id=x.chat_id).delete()
        await sync_to_async(del_chat)(chat)
    
    async def create_new_chat(self):
        logger.info("Creating new chat for session_id=%s", self.session.session_id)
        create_fun = lambda x: Chat.objects.create(session=self.session)
        chat = await sync_to_async(create_fun)(self.session)
        logger.info("Successfully created new chat_id=%s", chat.chat_id)
        
        return chat 
        
        