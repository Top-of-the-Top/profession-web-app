import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from apps.ai_chat_bot.services import YandexChatAIService
from apps.courses.models import Course
from ..models import Session
from .dto import (
    DeleteChatRequest,
    WsMessage,
    ChatCreatedMessage,
    ChatDeletedMessage,
    ConnectedMessage,
    ErrorMessage,
    FinishingAnswerMessage,
    GetHistoryRequest,
    HistoryReceivedMessage,
    SendMessageRequest,
    StartNewChatRequest,
    StartingAnswerMessage,
    StreamingResponseMessage,
    WsRequest,
    parse_ws_request,
)
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
  course_slug: str
  session: Session 
  chat_service: YandexChatAIService

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
        #if course not in self.user.aget_purchased_course_ids():
        #   raise Exception("User does not have access to this course")
        
        self.session = await self.chat_service.get_or_create_session(self.user, course)
        logger.info(
            "WS connect accepted: user_id=%s course_slug=%s session_id=%s",
            getattr(self.user, "pk", None),
            self.course_slug,
            self.session.session_id,
        )
        await self.accept()
        
        chats = await self.chat_service.get_chats()
        await self._send_ws_message(ConnectedMessage(chats=chats))
    except Exception as e:
        logger.exception("WS connect rejected (4500): course_slug=%s error=%s", self.course_slug, e)
        await self.close(code=4500)

  async def receive(self, text_data=None, bytes_data=None):
      if not text_data:
          return

      try:
          request = parse_ws_request(json.loads(text_data))
      except Exception:
          await self._send_ws_message(ErrorMessage(message="Unsupported message type"))
          return

      await self._handle_request(request)
              
  async def disconnect(self, close_code):
      logger.info(f"Socket closed. Event: {close_code}")

  async def _send_ws_message(self, ws_message: WsMessage):
      await self.send(text_data=json.dumps(ws_message.to_dict()))

  async def _handle_request(self, request: WsRequest):
      match request:
          case StartNewChatRequest():
              chat = await self.chat_service.create_new_chat()
              await self._send_ws_message(ChatCreatedMessage(chat_id=str(chat.chat_id)))
          case DeleteChatRequest(chat_id=chat_id):
              await self.chat_service.delete_chat(chat_id)
              await self._send_ws_message(ChatDeletedMessage())
          case GetHistoryRequest(chat_id=chat_id):
              history = await self.chat_service.get_chat_history(chat_id)
              await self._send_ws_message(
                  HistoryReceivedMessage(chat_id=chat_id, history=history)
              )
          case SendMessageRequest(chat_id=chat_id, content=content):
              user_message = str(content.get("text", "")).strip()
              chat = await self.chat_service.get_chat_for_current_session(chat_id)
              await self._send_ws_message(StartingAnswerMessage(chat_id=chat_id))
              await self.chat_service.save_message(chat, "user", user_message)
              full_ai_response = ""
              try:
                  stream = self.chat_service.ask_question_stream(user_message)
                  async for chunk in stream:
                      full_ai_response += chunk
                      await self._send_ws_message(
                          StreamingResponseMessage(chat_id=chat_id, chunk=chunk)
                      )
                  await self.chat_service.save_message(chat, "assistant", full_ai_response)
              except Exception as e:
                  await self._send_ws_message(ErrorMessage(message=str(e)))
              finally:
                  await self._send_ws_message(FinishingAnswerMessage(chat_id=chat_id))
          case _:
              await self._send_ws_message(ErrorMessage(message="Unsupported message type"))
