from django.test import TestCase, override_settings
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
import tempfile

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
        'course_id': course,
        'title': 'Тестовая секция',
    }
    defaults.update(kwargs)
    return Section.objects.create(**defaults)


def create_test_lesson(section, **kwargs):
    defaults = {
        'section_id': section,
        'title': 'Тестовый урок',
        'date_time': timezone.now() + timedelta(days=1),
    }
    defaults.update(kwargs)
    return Lesson.objects.create(**defaults)


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    BROKER_BACKEND='memory',
    CELERY_BROKER_URL='memory://'
)
class HomeworkDeadlineReminderRevokeSignalTest(TestCase):
    """Интеграционные тесты для сигналов ДЗ"""

    def setUp(self):
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

    def test_reminders_scheduled_on_creation(self):
        """При создании ДЗ планируются напоминания"""
        deadline = timezone.now() + timedelta(days=2)

        self.mock_revoke.reset_mock()

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Test Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_reminders_revoked_when_deadline_changed(self):
        """При изменении дедлайна старые напоминания отменяются"""
        old_deadline = timezone.now() + timedelta(days=2)
        self.mock_revoke.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )


        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        self.assertEqual(self.mock_revoke.call_count, 4)

    def test_reminders_revoked_when_homework_deleted(self):
        """При удалении ДЗ напоминания отменяются"""
        deadline = timezone.now() + timedelta(days=2)
        self.mock_revoke.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Test Homework',
            deadline=deadline
        )


        homework.delete()

        self.assertEqual(self.mock_revoke.call_count, 4)

    def test_revoke_not_called_when_deadline_unchanged(self):
        """При изменении только названия revoke не вызывается"""
        deadline = timezone.now() + timedelta(days=2)
        self.mock_revoke.reset_mock()


        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Original Title',
            deadline=deadline
        )


        homework.title = 'New Title'
        homework.save()

        self.mock_revoke.assert_not_called()

    def test_reminders_not_scheduled_when_deadline_in_past(self):
        """Если дедлайн в прошлом, напоминания не планируются"""
        past_deadline = timezone.now() - timedelta(days=1)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Past Homework',
            deadline=past_deadline
        )

        self.mock_apply_async.assert_not_called()
        self.mock_email_async.assert_not_called()

    def test_reminders_not_scheduled_when_deadline_less_than_1h(self):
        """Если до дедлайна меньше 1 часов, то только уведомление о создании"""
        now = timezone.now()
        deadline = now + timedelta(hours=1)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Soon Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 0)
        self.assertEqual(self.mock_email_async.call_count, 0)

    def test_reminders_not_scheduled_when_deadline_less_than_24h(self):
        """Если до дедлайна меньше 24 часов, то только уведомление о создании и дедлайн за 1 час"""
        now = timezone.now()
        deadline = now + timedelta(hours=23)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Soon Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)

    def test_reminders_not_scheduled_when_deadline_more_than_24h(self):
        """Если до дедлайна меньше 24 часов, то только уведомление о создании и дедлайн за 1 час"""
        now = timezone.now()
        deadline = now + timedelta(hours=27)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Soon Homework',
            deadline=deadline
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_revoke_not_called_when_deadline_same(self):
        """При сохранении с тем же дедлайном revoke не вызывается"""
        deadline = timezone.now() + timedelta(days=2)
        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Test Homework',
            deadline=deadline
        )

        self.mock_revoke.reset_mock()

        homework.save()

        self.mock_revoke.assert_not_called()



@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    BROKER_BACKEND='memory',
    CELERY_BROKER_URL='memory://'
)
class HomeworkNotificationDeadlineChangeTest(TestCase):
    """Интеграционные тесты уведомлений при изменении дедлайна"""

    def setUp(self):
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

    def test_notification_sent_when_deadline_extended(self):
        """При продлении дедлайна отправляется уведомление с ключевым словом 'продлён'"""
        old_deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        self.mock_send_course.assert_called_once()
        args = self.mock_send_course.call_args[0]
        title = args[1]
        message = args[2]

        self.assertIn('перенесён', title)
        self.assertIn('обновлен', message)
        self.assertIn(new_deadline.strftime('%d.%m %H:%M'), message)

    def test_notification_contains_new_deadlines(self):
        """Уведомление должно содержать новый дедлайн"""
        old_deadline = timezone.now() + timedelta(days=2)
        self.mock_send_course.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
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
        """При изменении только названия уведомление не отправляется"""
        deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Original Title',
            deadline=deadline
        )

        self.mock_send_course.reset_mock()



        homework.title = 'New Title'
        homework.save()

        self.mock_send_course.assert_not_called()

    def test_notification_sent_when_deadline_changed_even_with_title_change(self):
        """При одновременном изменении названия и дедлайна уведомление отправляется"""
        old_deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Original Title',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.title = 'New Title'
        homework.deadline = new_deadline
        homework.save()

        self.mock_send_course.assert_called_once()
        args = self.mock_send_course.call_args[0]
        message = args[2]

        self.assertIn(new_deadline.strftime('%d.%m %H:%M'), message)

    def test_notification_sent_on_homework_creation(self):
        """При создании ДЗ отправляется моментальное уведомление"""
        deadline = timezone.now() + timedelta(days=7)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='New Homework',
            deadline=deadline
        )

        self.mock_send_course.assert_called_once()
        args = self.mock_send_course.call_args[0]
        title = args[1]
        message = args[2]

        self.assertIn('Новое', title)
        self.assertIn(deadline.strftime('%d.%m %H:%M'), message)

    def test_notification_sent_when_deadline_extended_with_correct_text(self):
        """При продлении дедлайна уведомление содержит слово 'продлён'"""
        old_deadline = timezone.now() + timedelta(days=2)
        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Test Homework',
            deadline=old_deadline
        )

        self.mock_send_course.reset_mock()

        new_deadline = timezone.now() + timedelta(days=5)
        homework.deadline = new_deadline
        homework.save()

        args = self.mock_send_course.call_args[0]
        title = args[1]
        message = args[2]

        self.assertIn('перенесён', title)
        self.assertIn('обновлен', message)
    def test_notification_contains_old_deadline(self):
        """Уведомление должно содержать старый дедлайн"""
        old_deadline = timezone.now() + timedelta(days=2)
        homework = Homework.objects.create(
            lesson_id=self.lesson,
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
        """Автор получает уведомление о создании ДЗ"""
        user = create_test_user()

        deadline = timezone.now() + timedelta(days=7)
        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='New Homework',
            deadline=deadline,
            last_modified_by=user
        )

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertEqual(args[0], user.id)
        self.assertIn('прикреплено', args[2])

    def test_author_notified_on_homework_update(self):
        """Автор получает уведомление об изменении ДЗ"""
        user = create_test_user()

        deadline = timezone.now() + timedelta(days=7)
        homework = Homework.objects.create(
            lesson_id=self.lesson,
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
        self.assertIn('изменено', args[2])

@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    BROKER_BACKEND='memory',
    CELERY_BROKER_URL='memory://'
)
class LessonReminderSignalTest(TestCase):
    """Интеграционные тесты для сигналов урока (как у Homework)"""

    def setUp(self):
        self.celery_apply_async_patcher = patch('apps.courses.signals.send_course_notification.apply_async')
        self.email_apply_async_patcher = patch('apps.courses.signals.send_mass_course_email.apply_async')
        self.revoke_patcher = patch('celery.current_app.control.revoke')

        self.mock_apply_async = self.celery_apply_async_patcher.start()
        self.mock_email_async = self.email_apply_async_patcher.start()
        self.mock_revoke = self.revoke_patcher.start()

        self.course = create_test_course()
        self.section = create_test_section(self.course)

    def tearDown(self):
        self.celery_apply_async_patcher.stop()
        self.email_apply_async_patcher.stop()
        self.revoke_patcher.stop()


    def test_reminders_scheduled_on_lesson_creation(self):
        """При создании урока планируются напоминания (24h и 1h)"""
        date_time = timezone.now() + timedelta(days=2)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date_time
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_reminders_not_scheduled_when_date_in_past(self):
        """Если дата урока в прошлом, напоминания не планируются"""
        past_date = timezone.now() - timedelta(days=1)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Past Lesson',
            date_time=past_date
        )

        self.mock_apply_async.assert_not_called()
        self.mock_email_async.assert_not_called()

    def test_reminders_only_1h_scheduled_when_date_exactly_24h(self):
        """Если до урока ровно 24 часа, только 1h напоминание планируется"""
        date = timezone.now() + timedelta(hours=24)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)

    def test_reminders_only_1h_scheduled_when_date_between_1h_and_24h(self):
        """Если до урока 23 часа, только 1h напоминание планируется"""
        date = timezone.now() + timedelta(hours=23)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)

    def test_no_reminders_scheduled_when_date_less_than_1h(self):
        """Если до урока меньше 1 часа, напоминания не планируются"""
        date = timezone.now() + timedelta(minutes=30)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 0)
        self.assertEqual(self.mock_email_async.call_count, 0)

    def test_reminders_scheduled_when_date_more_than_24h(self):
        """Если до урока больше 24 часов, оба напоминания планируются"""
        date = timezone.now() + timedelta(days=2)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_reminders_revoked_when_date_changed(self):
        """При изменении даты урока старые напоминания отменяются"""
        old_date = timezone.now() + timedelta(days=2)
        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=old_date
        )

        self.mock_revoke.reset_mock()

        new_date = timezone.now() + timedelta(days=5)
        lesson.date_time = new_date
        lesson.save()

        self.assertEqual(self.mock_revoke.call_count, 4)

    def test_new_reminders_scheduled_when_date_changed(self):
        """При изменении даты урока планируются новые напоминания"""
        old_date = timezone.now() + timedelta(days=2)
        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=old_date
        )

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        new_date = timezone.now() + timedelta(days=5)
        lesson.date_time = new_date
        lesson.save()

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_revoke_not_called_when_date_unchanged(self):
        """При изменении только названия revoke не вызывается"""
        date = timezone.now() + timedelta(days=2)
        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Original Title',
            date_time=date
        )

        self.mock_revoke.reset_mock()

        lesson.title = 'New Title'
        lesson.save()

        self.mock_revoke.assert_not_called()

    def test_revoke_not_called_when_date_same(self):
        """При сохранении с той же датой revoke не вызывается"""
        date = timezone.now() + timedelta(days=2)
        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.mock_revoke.reset_mock()

        lesson.save()

        self.mock_revoke.assert_not_called()

    def test_reminders_revoked_when_lesson_deleted(self):
        """При удалении урока напоминания отменяются"""
        date_time = timezone.now() + timedelta(days=2)
        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date_time
        )

        self.mock_revoke.reset_mock()

        lesson.delete()

        self.assertEqual(self.mock_revoke.call_count, 4)


    def test_reminders_not_scheduled_when_date_less_than_24h(self):
        """Если до урока меньше 24 часов, то только 1h напоминание"""
        now = timezone.now()
        date = now + timedelta(hours=23)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Soon Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)

    def test_reminders_not_scheduled_when_date_less_than_1h(self):
        """Если до урока меньше 1 часа, напоминания не планируются"""
        now = timezone.now()
        date = now + timedelta(hours=1)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Soon Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 0)
        self.assertEqual(self.mock_email_async.call_count, 0)

    def test_reminders_scheduled_when_date_more_than_24h(self):
        """Если до урока больше 24 часов, оба напоминания планируются"""
        now = timezone.now()
        date = now + timedelta(hours=27)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Later Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 2)
        self.assertEqual(self.mock_email_async.call_count, 2)

    def test_reminders_24h_not_scheduled_when_date_exactly_24h(self):
        """Если до урока ровно 24 часа, 24h напоминание не планируется"""
        date = timezone.now() + timedelta(hours=24)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)

    def test_reminders_24h_not_scheduled_when_date_between_1h_and_24h(self):
        """Если до урока 23 часа, 24h напоминание не планируется"""
        date = timezone.now() + timedelta(hours=23)

        self.mock_apply_async.reset_mock()
        self.mock_email_async.reset_mock()

        lesson = Lesson.objects.create(
            section_id=self.section,
            title='Test Lesson',
            date_time=date
        )

        self.assertEqual(self.mock_apply_async.call_count, 1)
        self.assertEqual(self.mock_email_async.call_count, 1)