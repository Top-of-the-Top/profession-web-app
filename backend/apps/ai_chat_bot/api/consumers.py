import json
import logging
from channels.consumer import AsyncConsumer
from apps.ai_chat_bot.services import YandexChatAIService
from apps.courses.models import Course
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncConsumer):

  async def websocket_connect(self, event):
    self.course_slug = self.scope['url_route']['kwargs']['course_slug']
    self.user = self.scope['user']
    self.chat_service = YandexChatAIService()

    if self.user.is_anonymous:
        await self.send({"type": "websocket.close", "code": 4003})
        return

    try:
        course = await sync_to_async(Course.objects.get)(slug=self.course_slug)
        self.session = await self.chat_service.get_or_create_session(self.user, course)

        await self.send({
            "type": "websocket.accept"
        })
            
    except Exception as e:
        logger.error(f"Connect error: {e}")
        await self.send({"type": "websocket.close", "code": 4500})
  
  async def websocket_receive(self, event):
      text_data = event.get("text", None)
      if text_data:
          data = json.loads(text_data)
          user_message = data.get("message", "")
          await self.chat_service.save_message(self.session, 'user', user_message)

          full_ai_response = ""
          try:
              stream = await self.chat_service.ask_question_stream(self.session, user_message)

              async for chunk_event in stream:
                  if chunk_event.event == 'thread.message.delta':
                      chunk = chunk_event.data.delta.content[0].text.value
                      full_ai_response += chunk
                      
                      await self.send({
                          "type": "websocket.send",
                          "text": json.dumps({"type": "chunk", "content": chunk})
                      })

              await self.chat_service.save_message(self.session, 'assistant', full_ai_response)
          except Exception as e:
              await self.send({
                    "type": "websocket.send",
                    "text": json.dumps({"type": "error", "content": str(e)})
                })
              
  async def websocket_disconnect(self, event):
      logger.info(f"Socket closed. Event: {event}")
