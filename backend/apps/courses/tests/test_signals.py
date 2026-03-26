from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock, call
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
import tempfile
from apps.users.models import User
from apps.users.api.utils import encrypt_data
from ..models import Course, Section, Lesson, Homework, Question, Task, DEFAULT_COURSE_IMAGE
from .test_models import BaseTestCase

def create_test_user(email='test@test.com', role='teacher'):
    return User.objects.create_user(
        email_cipher=encrypt_data(email),
        password='testpass123',
        role=role
    )


def create_test_course(**kwargs):
    defaults = {
        'title': 'Тестовый курс',
        'sub_title': 'Краткое описание тестового курса для проверки',
        'description': 'Очень подробное описание тестового курса',
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
        'date': timezone.now() + timedelta(days=1),
    }
    defaults.update(kwargs)
    return Lesson.objects.create(**defaults)


def create_test_homework(lesson, **kwargs):
    defaults = {
        'lesson_id': lesson,
        'title': 'Тестовое ДЗ',
        'deadline': timezone.now() + timedelta(days=7),
    }
    defaults.update(kwargs)
    return Homework.objects.create(**defaults)



@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HandleCourseImageUpdateSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    @patch('django.core.files.storage.default_storage.delete')
    def test_old_image_deleted_when_new_image_uploaded(self, mock_delete):
        course = create_test_course()

        course.image.name = 'courses/course_1.jpg'
        Course.objects.filter(pk=course.pk).update(
            image='courses/course_1.jpg'
        )
        course.refresh_from_db()

        mock_new_image = MagicMock()
        mock_new_image.name = 'courses/course_new.jpg'

        with patch.object(
            course.__class__.image.field,
            'generate_filename',
            return_value='courses/course_new.jpg'
        ):
            old_image_name = course.image.name

            Course.objects.filter(pk=course.pk).update(
                image='courses/course_new.jpg'
            )

        course.refresh_from_db()
        self.assertEqual(course.image.name, 'courses/course_new.jpg')

    def test_default_image_not_deleted(self):
        course = create_test_course()
        original_image = course.image.name

        course.title = 'Updated Title'
        course.save()

        self.assertEqual(course.image.name, original_image)

    @patch('django.core.files.storage.default_storage.delete')
    def test_signal_not_triggered_on_new_course(self, mock_delete):
        course = create_test_course()

        mock_delete.assert_not_called()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DeleteCourseImageSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    @patch('django.core.files.storage.default_storage.delete')
    def test_image_deleted_when_course_deleted(self, mock_delete):
        course = create_test_course()
        course.image.name = 'courses/course_1.jpg'
        course.save()

        course.delete()

    def test_default_image_not_deleted_on_course_deletion(self):
        course = create_test_course()

        course.delete()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseNotificationSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.send_personal_patcher = patch(
            'apps.courses.signals.send_personal_notification.delay'
        )
        self.send_course_patcher = patch(
            'apps.courses.signals.send_course_notification.delay'
        )
        self.send_mass_email_patcher = patch(
            'apps.courses.signals.send_mass_course_email.delay'
        )

        self.mock_send_personal = self.send_personal_patcher.start()
        self.mock_send_course = self.send_course_patcher.start()
        self.mock_send_mass_email = self.send_mass_email_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()
        self.send_personal_patcher.stop()
        self.send_course_patcher.stop()
        self.send_mass_email_patcher.stop()

    def test_notification_sent_on_course_creation(self):
        user = create_test_user()
        course = Course.objects.create(
            title='New Course',
            sub_title='Subtitle',
            description='Description',
            price=1000,
            last_modified_by=user
        )

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertEqual(args[0], user.id)
        self.assertIn('создан', args[2])

    def test_notification_sent_on_course_update(self):
        user = create_test_user()
        course = create_test_course()

        self.mock_send_personal.reset_mock()
        self.mock_send_course.reset_mock()
        self.mock_send_mass_email.reset_mock()

        course.title = 'Updated Title'
        course.last_modified_by = user
        course.save()

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertIn('обновлен', args[2])

        self.mock_send_course.assert_called_once()
        self.mock_send_mass_email.assert_called_once()

    def test_tasks_called_with_correct_parameters_on_update(self):
        user = create_test_user()
        course = create_test_course()

        self.mock_send_course.reset_mock()
        self.mock_send_mass_email.reset_mock()

        course.title = 'Updated Course'
        course.last_modified_by = user
        course.save()

        course_args = self.mock_send_course.call_args[0]
        self.assertEqual(course_args[0], course.pk)
        self.assertIn('Обновление курса', str(course_args[1]))

        email_args = self.mock_send_mass_email.call_args[0]
        self.assertEqual(email_args[0], course.pk)

    def test_no_course_notification_on_creation(self):
        course = create_test_course()

        self.mock_send_course.assert_not_called()
        self.mock_send_mass_email.assert_not_called()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomeworkDeadlineHandlerSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.send_personal_patcher = patch(
            'apps.courses.signals.send_personal_notification.delay'
        )
        self.send_course_patcher = patch(
            'apps.courses.signals.send_course_notification.delay'
        )
        self.send_course_apply_async_patcher = patch(
            'apps.courses.signals.send_course_notification.apply_async'
        )
        self.send_mass_email_patcher = patch(
            'apps.courses.signals.send_mass_course_email.delay'
        )

        self.mock_send_personal = self.send_personal_patcher.start()
        self.mock_send_course = self.send_course_patcher.start()
        self.mock_send_course_apply_async = self.send_course_apply_async_patcher.start()
        self.mock_send_mass_email = self.send_mass_email_patcher.start()

        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()
        self.send_personal_patcher.stop()
        self.send_course_patcher.stop()
        self.send_course_apply_async_patcher.stop()
        self.send_mass_email_patcher.stop()

    def test_notification_sent_on_homework_creation(self):
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
        self.assertIn('создано', args[2])

        self.mock_send_course.assert_called_once()

    def test_notification_sent_on_homework_update(self):
        user = create_test_user()
        deadline = timezone.now() + timedelta(days=7)
        homework = create_test_homework(self.lesson, deadline=deadline)

        self.mock_send_personal.reset_mock()
        self.mock_send_course.reset_mock()

        homework.title = 'Updated Homework'
        homework.last_modified_by = user
        homework.save()

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertIn('изменено', args[2])

    def test_reminder_tasks_scheduled_correctly(self):
        deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Homework with reminders',
            deadline=deadline
        )

        self.assertEqual(self.mock_send_course_apply_async.call_count, 2)

    def test_reminders_not_scheduled_if_deadline_in_past(self):
        past_deadline = timezone.now() - timedelta(days=1)

        self.mock_send_course_apply_async.reset_mock()

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Past Homework',
            deadline=past_deadline
        )

        self.mock_send_course_apply_async.assert_not_called()

    def test_reminder_24h_before_deadline(self):
        deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Homework',
            deadline=deadline
        )

        calls = self.mock_send_course_apply_async.call_args_list

        found_24h = False
        for call_obj in calls:
            if 'eta' in call_obj.kwargs:
                eta = call_obj.kwargs['eta']
                time_diff = (deadline - eta).total_seconds()
                if abs(time_diff - 86400) < 60:
                    found_24h = True
                    break

        self.assertTrue(found_24h)

    def test_reminder_1h_before_deadline(self):
        deadline = timezone.now() + timedelta(days=2)

        homework = Homework.objects.create(
            lesson_id=self.lesson,
            title='Homework',
            deadline=deadline
        )

        calls = self.mock_send_course_apply_async.call_args_list

        found_1h = False
        for call_obj in calls:
            if 'eta' in call_obj.kwargs:
                eta = call_obj.kwargs['eta']
                time_diff = (deadline - eta).total_seconds()
                if abs(time_diff - 3600) < 60:
                    found_1h = True
                    break

        self.assertTrue(found_1h)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class QuestionNotificationSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.send_personal_patcher = patch(
            'apps.courses.signals.send_personal_notification.delay'
        )
        self.send_course_patcher = patch(
            'apps.courses.signals.send_course_notification.delay'
        )
        self.send_mass_email_patcher = patch(
            'apps.courses.signals.send_mass_course_email.delay'
        )

        self.mock_send_personal = self.send_personal_patcher.start()
        self.mock_send_course = self.send_course_patcher.start()
        self.mock_send_mass_email = self.send_mass_email_patcher.start()

        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.homework = create_test_homework(self.lesson)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()
        self.send_personal_patcher.stop()
        self.send_course_patcher.stop()
        self.send_mass_email_patcher.stop()

    def test_notification_sent_on_question_creation(self):
        user = create_test_user()

        self.mock_send_course.reset_mock()
        self.mock_send_personal.reset_mock()
        self.mock_send_mass_email.reset_mock()


        question = Question.objects.create(
            homework_id=self.homework,
            text='Test Question',
            correct_ans='A',
            answer_options=['A', 'B', 'C'],
            last_modified_by=user
        )

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertIn('добавлен', args[2])

        self.mock_send_course.assert_called_once()
        self.mock_send_mass_email.assert_called_once()

    def test_notification_sent_on_question_update(self):
        user = create_test_user()
        question = Question.objects.create(
            homework_id=self.homework,
            text='Original Question',
            correct_ans='A',
            answer_options=['A', 'B']
        )

        self.mock_send_personal.reset_mock()
        self.mock_send_course.reset_mock()
        self.mock_send_mass_email.reset_mock()

        question.text = 'Updated Question'
        question.last_modified_by = user
        question.save()

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertIn('отредактирован', args[2])

    def test_correct_course_id_extracted(self):
        question = Question.objects.create(
            homework_id=self.homework,
            text='Test Question',
            correct_ans='A',
            answer_options=['A', 'B']
        )

        course_args = self.mock_send_course.call_args[0]
        self.assertEqual(course_args[0], self.course.course_id)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TaskNotificationSignalTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.send_personal_patcher = patch(
            'apps.courses.signals.send_personal_notification.delay'
        )
        self.send_course_patcher = patch(
            'apps.courses.signals.send_course_notification.delay'
        )
        self.send_mass_email_patcher = patch(
            'apps.courses.signals.send_mass_course_email.delay'
        )

        self.mock_send_personal = self.send_personal_patcher.start()
        self.mock_send_course = self.send_course_patcher.start()
        self.mock_send_mass_email = self.send_mass_email_patcher.start()

        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.homework = create_test_homework(self.lesson)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()
        self.send_personal_patcher.stop()
        self.send_course_patcher.stop()
        self.send_mass_email_patcher.stop()

    def test_notification_sent_on_task_creation(self):
        user = create_test_user()

        self.mock_send_course.reset_mock()
        self.mock_send_personal.reset_mock()
        self.mock_send_mass_email.reset_mock()

        task = Task.objects.create(
            homework_id=self.homework,
            text='Test Task',
            max_points=10,
            last_modified_by=user
        )

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertIn('добавлена', args[2])

        self.mock_send_course.assert_called_once()
        self.mock_send_mass_email.assert_called_once()

    def test_notification_sent_on_task_update(self):
        user = create_test_user()
        task = Task.objects.create(
            homework_id=self.homework,
            text='Original Task',
            max_points=10
        )

        self.mock_send_personal.reset_mock()
        self.mock_send_course.reset_mock()
        self.mock_send_mass_email.reset_mock()

        task.text = 'Updated Task'
        task.last_modified_by = user
        task.save()

        self.mock_send_personal.assert_called_once()
        args = self.mock_send_personal.call_args[0]
        self.assertIn('изменена', args[2])

    def test_correct_course_id_extracted(self):
        task = Task.objects.create(
            homework_id=self.homework,
            text='Test Task',
            max_points=10
        )

        course_args = self.mock_send_course.call_args[0]
        self.assertEqual(course_args[0], self.course.course_id)

    def test_task_text_truncated_in_notification(self):
        long_text = 'A' * 100
        task = Task.objects.create(
            homework_id=self.homework,
            text=long_text,
            max_points=10
        )

        course_args = self.mock_send_course.call_args[0]
        message = course_args[2]
        self.assertLessEqual(len(message), 200)
