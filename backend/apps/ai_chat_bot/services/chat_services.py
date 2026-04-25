
import logging
from django.conf import settings
from apps.ai_chat_bot.models import ChatMessage, ChatSession
from asgiref.sync import sync_to_async
from apps.ai_chat_bot.services.base_service import YandexAIBase

logger = logging.getLogger(__name__)
class YandexChatAIService(YandexAIBase):
    
    async def get_or_create_session(self, user, course):
      logger.info(
          "Establishing connection to new chat session in course %s for user %s",
          course.pk,
          user.pk,
      )

      session, created = await sync_to_async(
          ChatSession.objects.get_or_create)(
              course=course,
              user=user
          )

      if created:
          logger.info("Created new chat session %s", session.chat_session_id)

      return session
    
    async def save_message(self, session, role, content):
        return await sync_to_async(ChatMessage.objects.create)(
            chat_session=session,
            role=role,
            content=content
        )
    
    async def ask_question_stream(self, session, text):
        logger.info("Create response stream for session %s", session.chat_session_id)
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
        