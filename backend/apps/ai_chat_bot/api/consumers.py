import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from apps.ai_chat_bot.services import YandexChatAIService
from apps.courses.models import Course
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):

  async def connect(self):
    self.course_slug = self.scope['url_route']['kwargs']['course_slug']
    self.user = self.scope['user']
    self.chat_service = YandexChatAIService()
    logger.info("WS connect attempt: course_slug=%s", self.course_slug)

    if self.user.is_anonymous:
        logger.warning("WS connect rejected (4003): anonymous user, course_slug=%s", self.course_slug)
        await self.close(code=4003)
        return

    try:
        course = await sync_to_async(Course.objects.get)(slug=self.course_slug)
        self.session = await self.chat_service.get_or_create_session(self.user, course)
        logger.info(
            "WS connect accepted: user_id=%s course_slug=%s session_id=%s",
            getattr(self.user, "pk", None),
            self.course_slug,
            self.session.chat_session_id,
        )
        await self.accept()
            
    except Exception as e:
        logger.exception("WS connect rejected (4500): course_slug=%s error=%s", self.course_slug, e)
        await self.close(code=4500)

  async def receive(self, text_data=None, bytes_data=None):
      if text_data:
          data = json.loads(text_data)
          user_message = data.get("message", "")
          await self.chat_service.save_message(self.session, 'user', user_message)

          full_ai_response = ""
          try:
              stream = self.chat_service.ask_question_stream(self.session, user_message)

              async for chunk in stream:
                  full_ai_response += chunk
                  await self.send(text_data=json.dumps({"type": "chunk", "content": chunk}))

              await self.chat_service.save_message(self.session, 'assistant', full_ai_response)
          except Exception as e:
              await self.send(text_data=json.dumps({"type": "error", "content": str(e)}))
              
  async def disconnect(self, close_code):
      logger.info(f"Socket closed. Event: {close_code}")
