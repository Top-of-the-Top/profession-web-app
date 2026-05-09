from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import TestCase

from apps.ai_chat_bot.models import Chat, Message, Session
from apps.ai_chat_bot.services.chat_services import YandexChatAIService
from apps.courses.tests.test_models import create_test_course, create_test_user


class YandexChatAIServiceOrmTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._openai_patcher = patch("apps.ai_chat_bot.services.base_service.openai.AsyncOpenAI")
        cls._openai_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._openai_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.user = create_test_user(email="ai_svc_student@test.com", role="student")
        self.course = create_test_course(title="Курс для AI")

    def test_get_or_create_session_is_idempotent_per_user_course(self):
        svc = YandexChatAIService()
        async_to_sync(svc.get_or_create_session)(self.user, self.course)
        async_to_sync(svc.get_or_create_session)(self.user, self.course)
        self.assertEqual(Session.objects.filter(user=self.user, course=self.course).count(), 1)

    def test_create_new_chat_attaches_to_session(self):
        svc = YandexChatAIService()
        async_to_sync(svc.get_or_create_session)(self.user, self.course)
        chat = async_to_sync(svc.create_new_chat)()
        self.assertEqual(chat.session_id, svc.session.session_id)
        self.assertEqual(Chat.objects.filter(session=svc.session).count(), 1)

    def test_save_message_and_history_order(self):
        svc = YandexChatAIService()
        async_to_sync(svc.get_or_create_session)(self.user, self.course)
        chat = async_to_sync(svc.create_new_chat)()
        async_to_sync(svc.save_message)(chat, "user", "Первое")
        async_to_sync(svc.save_message)(chat, "assistant", "Второе")
        hist = async_to_sync(svc.get_chat_history)(str(chat.chat_id))
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0].role, "user")
        self.assertEqual(hist[1].role, "assistant")

    def test_delete_chat_removes_messages_cascade(self):
        svc = YandexChatAIService()
        async_to_sync(svc.get_or_create_session)(self.user, self.course)
        chat = async_to_sync(svc.create_new_chat)()
        async_to_sync(svc.save_message)(chat, "user", "x")
        self.assertEqual(Message.objects.count(), 1)
        async_to_sync(svc.delete_chat)(str(chat.chat_id))
        self.assertFalse(Chat.objects.filter(chat_id=chat.chat_id).exists())
        self.assertEqual(Message.objects.count(), 0)
