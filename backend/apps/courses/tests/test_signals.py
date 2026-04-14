from django.test import TestCase
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.courses.models import Course, Section, Lesson, Homework
from apps.users.api.utils import encrypt_data


def create_test_user(email='test@test.com', role='teacher'):
    return User.objects.create_user(
        email_cipher=encrypt_data(email),
        password='testpass123',
        role=role
    )


def create_test_course(**kwargs):
    defaults = {
        'title': 'Тестовый курс',
        'sub_title': 'Краткое описание',
        'description': 'Описание',
        'price': 9000,
    }
    defaults.update(kwargs)
    return Course.objects.create(**defaults)


def create_test_section(course, **kwargs):
    defaults = {
        'course': course,
        'title': 'Тестовая секция',
    }
    defaults.update(kwargs)
    return Section.objects.create(**defaults)


def create_test_lesson(section, **kwargs):
    defaults = {
        'section': section,
        'title': 'Тестовый урок',
    }
    defaults.update(kwargs)
    return Lesson.objects.create(**defaults)


class BaseTestCase(TestCase):
    """Базовый класс для тестов сигналов с мокированием всех внешних зависимостей"""

    CELERY_TASKS_TO_MOCK = [
        'apps.courses.signals.send_course_notification.delay',
        'apps.courses.signals.send_course_notification.apply_async',
        'apps.courses.signals.send_personal_notification.delay',
        'apps.courses.signals.send_mass_course_email.delay',
        'apps.courses.signals.send_mass_course_email.apply_async',
        'apps.courses.signals.send_mass_system_email.delay',
        'apps.courses.signals.send_single_email.delay',
        'apps.notifications.tasks.send_course_notification.delay',
        'apps.notifications.tasks.send_course_notification.apply_async',
        'apps.notifications.tasks.send_personal_notification.delay',
        'apps.notifications.tasks.send_mass_course_email.delay',
        'apps.notifications.tasks.send_mass_course_email.apply_async',
        'apps.notifications.rabbit.publish_event',
        'pika.BlockingConnection',
    ]

    def setUp(self):
        super().setUp()

        self.celery_patchers = []
        for task_path in self.CELERY_TASKS_TO_MOCK:
            patcher = patch(task_path)
            patcher.start()
            self.celery_patchers.append(patcher)

        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()

    def tearDown(self):
        for patcher in self.celery_patchers:
            patcher.stop()
        self.storage_patcher.stop()
        super().tearDown()


class HomeworkDeadlineReminderRevokeSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.celery_apply_async_patcher = patch('apps.courses.signals.send_course_notification.apply_async')
        self.email_apply_async_patcher = patch('apps.courses.signals.send_mass_course_email.apply_async')
        self.revoke_patcher = patch('celery.current_app.control.revoke')

        self.mock_apply_async = self.celery_apply_async_patcher.start()
        self.mock_email_async = self.email_apply_async_patcher.start()
        self.mock_revoke = self.revoke_patcher.start()

        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    def tearDown(self):
        self.celery_apply_async_patcher.stop()
        self.email_apply_async_patcher.stop()
        self.revoke_patcher.stop()
        super().tearDown()

    def test_reminders_scheduled_on_creation(self):
        deadline = timezone.now() + timedelta(days=2)

        self.mock_revoke.reset_mock()
        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_reminders_revoked_when_deadline_changed(self):
        old_deadline = timezone.now() + timedelta(days=2)
        self.mock_revoke.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        self.assertEqual(self.mock_revoke.call_count, 4)

    def test_reminders_revoked_when_homework_deleted(self):
        deadline = timezone.now() + timedelta(days=2)
        self.mock_revoke.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=deadline
        )

        homework.delete()

        self.assertEqual(self.mock_revoke.call_count, 4)

    def test_revoke_not_called_when_deadline_unchanged(self):
        deadline = timezone.now() + timedelta(days=2)
        self.mock_revoke.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Original Title',
            deadline=deadline
        )

        homework.title = 'New Title'
        homework.save()

        self.mock_revoke.assert_not_called()

    def test_reminders_not_scheduled_when_deadline_in_past(self):
        past_deadline = timezone.now() - timedelta(days=1)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Past Homework',
            deadline=past_deadline
        )

        self.mock_apply_async.assert_not_called()
        self.mock_email_async.assert_not_called()

    def test_reminders_not_scheduled_when_deadline_less_than_1h(self):
        now = timezone.now()
        deadline = now + timedelta(hours=1)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Soon Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 0)
        self.assertEqual(self.mock_email_async.call_count, 0)

    def test_reminders_not_scheduled_when_deadline_less_than_24h(self):
        now = timezone.now()
        deadline = now + timedelta(hours=23)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Soon Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)

    def test_reminders_not_scheduled_when_deadline_more_than_24h(self):
        now = timezone.now()
        deadline = now + timedelta(hours=27)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Soon Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_revoke_not_called_when_deadline_same(self):
        deadline = timezone.now() + timedelta(days=2)
        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=deadline
        )

        self.mock_revoke.reset_mock()
        homework.save()

        self.mock_revoke.assert_not_called()


class HomeworkNotificationDeadlineChangeTest(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.send_course_patcher = patch('apps.courses.signals.send_course_notification.delay')
        self.send_personal_patcher = patch('apps.courses.signals.send_personal_notification.delay')
        self.email_async_patcher = patch('apps.courses.signals.send_mass_course_email.apply_async')

        self.mock_send_course = self.send_course_patcher.start()
        self.mock_send_personal = self.send_personal_patcher.start()
        self.mock_email_async = self.email_async_patcher.start()

        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    def tearDown(self):
        self.send_course_patcher.stop()
        self.send_personal_patcher.stop()
        self.email_async_patcher.stop()
        super().tearDown()

    def test_notification_sent_when_deadline_extended(self):
        old_deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        self.mock_send_course.assert_called_once()

    def test_notification_contains_new_deadlines(self):
        old_deadline = timezone.now() + timedelta(days=2)
        self.mock_send_course.reset_mock()

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        args = self.mock_send_course.call_args[0]
        message = args[2]

        self.assertIn(new_deadline.strftime('%d.%m %H:%M'), message)

    def test_notification_not_sent_when_only_title_changed(self):
        deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Original Title',
            deadline=deadline
        )

        self.mock_send_course.reset_mock()

        homework.title = 'New Title'
        homework.save()

        self.mock_send_course.assert_not_called()

    def test_notification_sent_when_deadline_changed_even_with_title_change(self):
        old_deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Original Title',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.title = 'New Title'
        homework.deadline = new_deadline
        homework.save()

        self.mock_send_course.assert_called_once()

    def test_notification_sent_on_homework_creation(self):
        deadline = timezone.now() + timedelta(days=7)

        homework = Homework.objects.create(
            lesson=self.lesson,
            title='New Homework',
            deadline=deadline
        )

        self.mock_send_course.assert_called_once()

    def test_notification_sent_when_deadline_extended_with_correct_text(self):
        old_deadline = timezone.now() + timedelta(days=2)
        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        args = self.mock_send_course.call_args[0]
        title = args[1]
        self.assertIn('перенесён', title)

    def test_notification_contains_old_deadline(self):
        old_deadline = timezone.now() + timedelta(days=2)
        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        args = self.mock_send_course.call_args[0]
        message = args[2]
        self.assertIn(new_deadline.strftime('%d.%m %H:%M'), message)

    def test_author_notified_on_homework_creation(self):
        user = create_test_user()

        deadline = timezone.now() + timedelta(days=7)
        homework = Homework.objects.create(
            lesson=self.lesson,
            title='New Homework',
            deadline=deadline,
            last_modified_by=user
        )

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertEqual(args[0], user.id)

    def test_author_notified_on_homework_update(self):
        user = create_test_user()

        deadline = timezone.now() + timedelta(days=7)
        homework = Homework.objects.create(
            lesson=self.lesson,
            title='Original Title',
            deadline=deadline
        )

        self.mock_send_personal.reset_mock()

        homework.title = 'Updated Title'
        homework.last_modified_by = user
        homework.save()

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertEqual(args[0], user.id)
