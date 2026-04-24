
import logging
import os
import openai
import asyncio
from django.conf import settings
from apps.courses.models import Course
from apps.ai_chat_bot.models import ChatMessage, ChatSession
from asgiref.sync import sync_to_async
from apps.ai_chat_bot.services.base_service import YandexAIBase

logger = logging.getLogger(__name__)


class YandexChatAIService(YandexAIBase):
    
    async def get_or_create_session(self, user, course):
      logger.info(f"Establishing connection to new chat session in course {course.id} for user {user.user_id}")

      session, created = await sync_to_async(
          ChatSession.objects.get_or_create)(
              course=course,
              user=user
          )

      if created:
          try:
            async with self._semaphore:
                thread = await self.client.beta.threads.create()
                session.yandex_thread_id = thread.id
                await sync_to_async(session.save)()
                logger.info(f"Created new thread {thread.id} for session {session.chat_session_id}")
          except Exception as e:
              logger.error(f"Error in creating new thread: {e}")
              raise 

      return session
    
    async def save_message(self, session, role, content):
        return await sync_to_async(ChatMessage.objects.create)(
            chat_session=session,
            role=role,
            content=content
        )
    
    async def ask_question_stream(self, session, text):
        thread_id = session.yandex_thread_id
        vs_id = session.course.yandex_vs_id

        logger.info(f"Create new message in thread {thread_id}")
        try:
          async with self._semaphore:
              await self.client.beta.threads.messages.create(
                  thread_id=thread_id,
                  role="user",
                  content=text
              )


              stream = await self.client.beta.threads.runs.create(
                  thread_id=thread_id,
                  assistant_id=settings.YANDEX_ASSISTANT_ID,
                  tool_resources={"file_search": {"vector_store_ids": [vs_id]}},
                  stream=True
              )
              return stream
        
        except Exception as e:
            logger.error(f"Error while creating a new message in thread: {e}")
            raise 
        