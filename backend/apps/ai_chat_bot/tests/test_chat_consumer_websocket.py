from unittest.mock import patch
from urllib.parse import quote
from uuid import UUID

from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from apps.ai_chat_bot.models import Chat, Message, Session
from apps.courses.tests.test_models import create_test_course, create_test_user
from apps.users.api.utils.token_utils import get_tokens_for_user


class StubYandexChatAIService:
    def __init__(self):
        self.session = None

    async def get_or_create_session(self, user, course):
        def _go():
            s, _ = Session.objects.get_or_create(user=user, course=course)
            return s

        self.session = await sync_to_async(_go)()
        return self.session

    async def get_chats(self):
        def _list():
            return list(Chat.objects.filter(session=self.session).order_by("-updated_at"))

        return await sync_to_async(_list)()

    async def create_new_chat(self):
        def _mk():
            return Chat.objects.create(session=self.session)

        return await sync_to_async(_mk)()

    async def delete_chat(self, chat_id):
        def _rm():
            Chat.objects.filter(chat_id=chat_id, session=self.session).delete()

        await sync_to_async(_rm)()

    async def get_chat_history(self, chat_id):
        chat = await self.get_chat_for_current_session(chat_id)

        def _msgs():
            return list(chat.messages.all().order_by("updated_at"))

        return await sync_to_async(_msgs)()

    async def get_chat_for_current_session(self, chat_id):
        def _get():
            return Chat.objects.get(chat_id=chat_id, session=self.session)

        return await sync_to_async(_get)()

    async def save_message(self, chat, role, content):
        def _save():
            return Message.objects.create(chat=chat, role=role, content=content)

        return await sync_to_async(_save)()

    async def ask_question_stream(self, text):
        yield "Ок"


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    },
)
class ChatConsumerWebSocketTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.user = create_test_user(email="ai_ws_student@test.com", role="student")
        self.course = create_test_course(title="Курс WebSocket AI")
        tokens = get_tokens_for_user(self.user)
        self.access = tokens["access_token"]

    def _path(self, slug: str, token: str | None = None) -> str:
        base = f"/api/v1/courses/{slug}/ai/chat/"
        if token is None:
            return base
        return f"{base}?token={quote(token, safe='')}"

    def _run_async(self, async_fn):
        return async_to_sync(async_fn)()

    def test_anonymous_connection_rejected(self):
        async def _go():
            from project.asgi import application

            comm = WebsocketCommunicator(application, self._path(self.course.slug))
            connected, _ = await comm.connect()
            self.assertFalse(connected)

        self._run_async(_go)

    def test_unknown_course_closes_before_accept(self):
        async def _go():
            from project.asgi import application

            comm = WebsocketCommunicator(
                application,
                self._path("no-such-course-slug-999", self.access),
            )
            connected, _ = await comm.connect()
            self.assertFalse(connected)

        self._run_async(_go)

    @patch(
        "apps.ai_chat_bot.api.consumers.YandexChatAIService",
        side_effect=lambda: StubYandexChatAIService(),
    )
    def test_authenticated_connect_then_send_message_persists_roundtrip(self, _mock_cls):
        captured = {}

        async def _go():
            from project.asgi import application

            comm = WebsocketCommunicator(
                application,
                self._path(self.course.slug, self.access),
            )
            self.assertTrue((await comm.connect())[0])

            hello = await comm.receive_json_from()
            self.assertEqual(hello["type"], "connected")

            await comm.send_json_to({"type": "start new chat"})
            created = await comm.receive_json_from()
            self.assertEqual(created["type"], "chat created")
            captured["chat_id"] = created["chat_id"]

            await comm.send_json_to(
                {
                    "type": "send message",
                    "chat_id": captured["chat_id"],
                    "content": {"text": "Вопрос"},
                }
            )

            self.assertEqual((await comm.receive_json_from())["type"], "starting answer")
            stream = await comm.receive_json_from()
            self.assertEqual(stream["type"], "streaming response")
            self.assertEqual(stream["content"]["chunk"], "Ок")
            self.assertEqual((await comm.receive_json_from())["type"], "finishing answer")

            await comm.disconnect()

        self._run_async(_go)

        uid = UUID(captured["chat_id"])
        msgs = list(Message.objects.filter(chat__chat_id=uid).order_by("created_at"))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, "user")
        self.assertEqual(msgs[0].content, "Вопрос")
        self.assertEqual(msgs[1].role, "assistant")
        self.assertEqual(msgs[1].content, "Ок")

        self.assertEqual(Session.objects.filter(user=self.user, course=self.course).count(), 1)

    @patch(
        "apps.ai_chat_bot.api.consumers.YandexChatAIService",
        side_effect=lambda: StubYandexChatAIService(),
    )
    def test_malformed_client_payload_returns_error_type(self, _mock_cls):
        async def _go():
            from project.asgi import application

            comm = WebsocketCommunicator(
                application,
                self._path(self.course.slug, self.access),
            )
            self.assertTrue((await comm.connect())[0])
            await comm.receive_json_from()

            await comm.send_json_to({"type": "totally unknown"})
            err = await comm.receive_json_from()
            self.assertEqual(err["type"], "error")
            await comm.disconnect()

        self._run_async(_go)
