from unittest.mock import call, patch

from django.test import TestCase

from apps.ai_chat_bot.models import Chat, Message, Session
from apps.courses.models import Section
from apps.courses.tests.test_models import create_test_course, create_test_user


def make_session(user, course):
    return Session.objects.create(user=user, course=course)


def make_chat(session, title=None):
    return Chat.objects.create(session=session, title=title)


class MessageSignalTests(TestCase):

    def setUp(self):
        self.user = create_test_user(email="sig_user@test.local", role="student")
        self.course = create_test_course(title="Signal Course")
        self.session = make_session(self.user, self.course)
        self.chat = make_chat(self.session)

    def test_signal_updates_chat_updated_at(self):
        old_updated_at = self.chat.updated_at
        Message.objects.create(chat=self.chat, role="user", content="Hello")
        self.chat.refresh_from_db()
        self.assertGreaterEqual(self.chat.updated_at, old_updated_at)

    def test_signal_sets_chat_title_from_first_message(self):
        self.assertIsNone(self.chat.title)
        Message.objects.create(chat=self.chat, role="user", content="What is ML?")
        self.chat.refresh_from_db()
        self.assertIsNotNone(self.chat.title)
        self.assertIn("What is ML?", self.chat.title)

    def test_signal_does_not_overwrite_existing_title(self):
        chat = make_chat(self.session, title="Existing Title")
        Message.objects.create(chat=chat, role="user", content="New message content")
        chat.refresh_from_db()
        self.assertEqual(chat.title, "Existing Title")

    def test_signal_truncates_title_at_100_chars(self):
        long_content = "a" * 200
        Message.objects.create(chat=self.chat, role="user", content=long_content)
        self.chat.refresh_from_db()
        if self.chat.title:
            self.assertLessEqual(len(self.chat.title), 100)

    def test_signal_fires_for_assistant_messages_too(self):
        Message.objects.create(chat=self.chat, role="assistant", content="I can help!")
        self.chat.refresh_from_db()
        self.assertIsNotNone(self.chat.updated_at)


class SynchronizeCourseContextTaskTests(TestCase):

    def setUp(self):
        self.course = create_test_course(title="Sync Course")

    @patch("apps.ai_chat_bot.tasks.logger")
    def test_task_logs_error_when_course_not_found(self, mock_logger):
        from apps.ai_chat_bot.tasks import synchronize_course_context

        synchronize_course_context(99999999)
        mock_logger.error.assert_called()

    @patch("apps.ai_chat_bot.tasks.logger")
    @patch("apps.courses.models.Course.prepare_files_for_vs", side_effect=Exception("boom"))
    def test_task_logs_error_on_exception(self, _mock_content, mock_logger):
        from apps.ai_chat_bot.tasks import synchronize_course_context

        synchronize_course_context(str(self.course.course_id))
        mock_logger.error.assert_called()
        call_args = mock_logger.error.call_args.args[0]
        self.assertIn("Error syncing", call_args)


class AIChatModelTests(TestCase):

    def setUp(self):
        self.user = create_test_user(email="ai_model_st@test.local", role="student")
        self.course = create_test_course(title="AI Course")

    def test_session_str(self):
        session = Session.objects.create(user=self.user, course=self.course)
        s = str(session)
        self.assertIsInstance(s, str)

    def test_chat_str_with_title(self):
        session = Session.objects.create(user=self.user, course=self.course)
        chat = Chat.objects.create(session=session, title="My Chat")
        self.assertEqual(str(chat), "My Chat")

    def test_chat_str_without_title(self):
        session = Session.objects.create(user=self.user, course=self.course)
        chat = Chat.objects.create(session=session)
        s = str(chat)
        self.assertIsInstance(s, str)

    def test_message_str(self):
        session = Session.objects.create(user=self.user, course=self.course)
        chat = Chat.objects.create(session=session, title="t")
        msg = Message.objects.create(chat=chat, role="user", content="Hello world")
        s = str(msg)
        self.assertIn("user", s)
        self.assertIn("Hello world", s)

    def test_session_cascade_deleted_with_user(self):
        session = Session.objects.create(user=self.user, course=self.course)
        sid = session.session_id
        self.user.delete()
        self.assertFalse(Session.objects.filter(session_id=sid).exists())

    def test_chat_cascade_deleted_with_session(self):
        session = Session.objects.create(user=self.user, course=self.course)
        chat = Chat.objects.create(session=session, title="t")
        cid = chat.chat_id
        session.delete()
        self.assertFalse(Chat.objects.filter(chat_id=cid).exists())

    def test_message_cascade_deleted_with_chat(self):
        session = Session.objects.create(user=self.user, course=self.course)
        chat = Chat.objects.create(session=session, title="t")
        msg = Message.objects.create(chat=chat, role="user", content="test")
        mid = msg.message_id
        chat.delete()
        self.assertFalse(Message.objects.filter(message_id=mid).exists())

    def test_message_role_choices(self):
        roles = [r[0] for r in Message.ROLE_CHOICES]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

    def test_session_ordering_newest_first(self):
        s1 = Session.objects.create(user=self.user, course=self.course)
        course2 = create_test_course(title="AI Course 2")
        s2 = Session.objects.create(user=self.user, course=course2)
        sessions = list(Session.objects.filter(user=self.user))
        self.assertEqual(sessions[0], s2)


class RebuildAllCoursesVsTests(TestCase):

    @patch("apps.ai_chat_bot.tasks.synchronize_course_context")
    def test_queues_only_courses_with_sections(self, mock_sync):
        course_with = create_test_course(title="С секцией")
        Section.objects.create(course=course_with, title="Секция")

        course_without = create_test_course(title="Без секций")

        from apps.ai_chat_bot.tasks import rebuild_all_courses_vs
        rebuild_all_courses_vs()

        called_ids = {c.args[0] for c in mock_sync.delay.call_args_list}
        self.assertIn(course_with.pk, called_ids)
        self.assertNotIn(course_without.pk, called_ids)

    @patch("apps.ai_chat_bot.tasks.synchronize_course_context")
    def test_skips_deleted_courses(self, mock_sync):
        course = create_test_course(title="Удалённый курс")
        course.is_deleted = True
        course.save(update_fields=["is_deleted"])
        Section.objects.create(course=course, title="Секция")

        from apps.ai_chat_bot.tasks import rebuild_all_courses_vs
        rebuild_all_courses_vs()

        mock_sync.delay.assert_not_called()
