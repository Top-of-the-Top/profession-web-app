import json
import logging
from collections import deque

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.ai_chat_bot.services import YandexChatAIService
from apps.courses.models import Course

from ..models import Session
from .dto import (
    ChatCreatedMessage,
    ChatDeletedMessage,
    ConnectedMessage,
    DeleteChatRequest,
    ErrorMessage,
    FinishingAnswerMessage,
    GetHistoryRequest,
    HistoryReceivedMessage,
    SendMessageRequest,
    StartingAnswerMessage,
    StartNewChatRequest,
    StreamingResponseMessage,
    WsMessage,
    WsRequest,
    parse_ws_request,
)

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    course_slug: str
    session: Session
    group_name: str
    session_chat_history: dict[str, deque]
    chat_service: YandexChatAIService

    async def connect(self):
        self.session_chat_history = {}
        self.course_slug = self.scope["url_route"]["kwargs"]["course_slug"]
        self.user = self.scope["user"]
        self.chat_service = YandexChatAIService()
        logger.info("WS connect attempt: course_slug=%s", self.course_slug)

        if self.user.is_anonymous:
            logger.warning(
                "WS connect rejected (4003): anonymous user, course_slug=%s",
                self.course_slug,
            )
            await self.close(code=4003)
            return

        try:
            course = await sync_to_async(Course.objects.get, thread_sensitive=False)(
                slug=self.course_slug
            )
            self.session = await self.chat_service.get_or_create_session(self.user, course)

            logger.info(
                "WS connect accepted: user_id=%s course_slug=%s session_id=%s",
                getattr(self.user, "pk", None),
                self.course_slug,
                self.session.session_id,
            )

            self.group_name = f"session_{self.session.session_id}"

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            chats = await self.chat_service.get_chats()
            await self._send_ws_message(ConnectedMessage(chats=chats))
        except Exception as e:
            logger.exception(
                "WS connect rejected (4500): course_slug=%s error=%s",
                self.course_slug,
                e,
            )
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
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
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
                self.session_chat_history[chat_id] = deque(maxlen=20)
                for message in history:
                    self.session_chat_history[chat_id].append(f"{message.role}: {message.content}")
                await self._send_ws_message(
                    HistoryReceivedMessage(chat_id=chat_id, history=history)
                )
            case SendMessageRequest(chat_id=chat_id, content=content):
                user_message = str(content.get("text", "")).strip()
                if chat_id not in self.session_chat_history:
                    self.session_chat_history[chat_id] = deque(maxlen=20)
                    history = await self.chat_service.get_chat_history(chat_id)
                    for message in history:
                        self.session_chat_history[chat_id].append(
                            f"{message.role}: {message.content}"
                        )
                self.session_chat_history[chat_id].append(f"user: {user_message}")
                chat = await self.chat_service.get_chat_for_current_session(chat_id)
                await self._send_ws_message(StartingAnswerMessage(chat_id=chat_id))
                await self.chat_service.save_message(chat, "user", user_message)

                ai_chat_context = "\n".join(self.session_chat_history[chat_id])

                full_ai_response = ""
                try:
                    stream = self.chat_service.ask_question_stream(ai_chat_context)
                    async for chunk in stream:
                        full_ai_response += chunk
                        await self._send_ws_message(
                            StreamingResponseMessage(chat_id=chat_id, chunk=chunk)
                        )
                    self.session_chat_history[chat_id].append(f"assistant: {full_ai_response}")
                    await self.chat_service.save_message(chat, "assistant", full_ai_response)
                except Exception as e:
                    await self._send_ws_message(ErrorMessage(message=str(e)))
                finally:
                    await self._send_ws_message(FinishingAnswerMessage(chat_id=chat_id))
            case _:
                await self._send_ws_message(ErrorMessage(message="Unsupported message type"))
