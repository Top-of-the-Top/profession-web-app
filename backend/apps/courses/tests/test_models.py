from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock, Mock
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
import tempfile
from django.db.utils import IntegrityError
from apps.users.models import User
from apps.users.api.utils import encrypt_data
from apps.payments.models import Payment
from ..models import (
    Course, Section, Lesson, Homework, Question, Task,
    Users_Homeworks_Attempts, Users_questions_answers, Users_tasks_answers,
    PurchasedCourse, DEFAULT_COURSE_IMAGE, generate_unique_slug, course_image_path
)


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

class BaseTestCase(TestCase):

    CELERY_TASKS_TO_MOCK = [
        'apps.courses.signals.send_course_notification.delay',
        'apps.courses.signals.send_course_notification.apply_async',
        'apps.courses.signals.send_personal_notification.delay',
        'apps.courses.signals.send_mass_course_email.delay',
        'apps.courses.signals.send_mass_system_email.delay',
        'apps.courses.signals.send_single_email.delay',
    ]

    def setUp(self):
        self.celery_patchers = [
            patch(task) for task in self.CELERY_TASKS_TO_MOCK
        ]
        self.celery_mocks = [p.start() for p in self.celery_patchers]

    def tearDown(self):
        for patcher in self.celery_patchers:
            patcher.stop()


class GenerateUniqueSlugTest(BaseTestCase):

    def test_slug_generation_from_title(self):
        mock_instance = Mock()
        slug = generate_unique_slug(mock_instance, 'Python для начинающих')

        self.assertIn('python', slug)
        self.assertIn('dlia', slug)
        self.assertIn('-', slug)

    def test_slug_generation_with_empty_title(self):
        mock_instance = Mock()
        slug = generate_unique_slug(mock_instance, '')

        self.assertIn('title', slug)
        self.assertIn('-', slug)

    def test_slug_generation_with_non_ascii_title(self):
        mock_instance = Mock()
        slug = generate_unique_slug(mock_instance, '中文标题')

        self.assertIsNotNone(slug)
        self.assertIn('-', slug)

    def test_slug_has_uuid_part(self):
        mock_instance = Mock()
        slug = generate_unique_slug(mock_instance, 'Test Title')

        parts = slug.split('-')
        self.assertGreater(len(parts), 1)
        self.assertEqual(len(parts[-1]), 8)

    def test_slug_uniqueness_for_same_title(self):
        mock_instance = Mock()
        slug1 = generate_unique_slug(mock_instance, 'Same Title')
        slug2 = generate_unique_slug(mock_instance, 'Same Title')

        self.assertNotEqual(slug1, slug2)

    def test_slug_truncates_long_title(self):
        mock_instance = Mock()
        long_title = 'A' * 100
        slug = generate_unique_slug(mock_instance, long_title)

        self.assertLessEqual(len(slug), 89)


class CourseImagePathTest(BaseTestCase):

    def test_image_path_generation_with_jpg(self):
        mock_instance = Mock()
        mock_instance.pk = 123

        path = course_image_path(mock_instance, 'test.jpg')

        self.assertEqual(path, 'courses/course_123.jpg')

    def test_image_path_generation_with_png(self):
        mock_instance = Mock()
        mock_instance.pk = 456

        path = course_image_path(mock_instance, 'image.png')

        self.assertEqual(path, 'courses/course_456.png')

    def test_image_path_generation_with_uppercase_extension(self):
        mock_instance = Mock()
        mock_instance.pk = 789

        path = course_image_path(mock_instance, 'photo.PNG')

        self.assertEqual(path, 'courses/course_789.png')

    def test_image_path_generation_with_multiple_dots(self):
        mock_instance = Mock()
        mock_instance.pk = 999

        path = course_image_path(mock_instance, 'my.test.image.jpeg')

        self.assertEqual(path, 'courses/course_999.jpeg')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseSlugTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_slug_auto_generated_on_create(self):
        course = create_test_course(title='Python для начинающих')
        self.assertIsNotNone(course.slug)
        self.assertNotEqual(course.slug, '')

    def test_slug_contains_title(self):
        course = create_test_course(title='Python курс')
        self.assertIn('python', course.slug)

    def test_slug_is_unique_for_same_title(self):
        course1 = create_test_course(title='Python курс')
        course2 = create_test_course(title='Python курс')
        self.assertNotEqual(course1.slug, course2.slug)

    def test_slug_not_overwritten_on_update(self):
        course = create_test_course(title='Python курс')
        original_slug = course.slug

        course.title = 'Новое название'
        course.save()
        course.refresh_from_db()

        self.assertEqual(course.slug, original_slug)

    def test_slug_has_no_special_characters(self):
        course = create_test_course(title='Python для начинающих!')
        self.assertNotIn(' ', course.slug)
        self.assertNotIn('!', course.slug)

    def test_manual_slug_not_overwritten(self):
        course = create_test_course(title='Test Course', slug='custom-slug-12345678')
        self.assertEqual(course.slug, 'custom-slug-12345678')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseImageUrlTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_image_url_returns_s3_url_for_default_image(self):
        course = create_test_course()
        url = course.image_url
        self.assertIn('yandexcloud.net', url)
        self.assertIn(DEFAULT_COURSE_IMAGE, url)

    def test_image_url_contains_bucket_name(self):
        course = create_test_course()
        with patch('os.getenv', return_value='test-bucket'):
            url = course.image_url
            self.assertIn('test-bucket', url)

    @patch('django.core.files.storage.default_storage.url')
    def test_image_url_returns_custom_url_when_image_exists(self, mock_url):
        mock_url.return_value = '/media/courses/course_1.jpg'

        course = create_test_course()
        course.image.name = 'courses/course_1.jpg'
        course.save()

        url = course.image_url
        self.assertEqual(url, '/media/courses/course_1.jpg')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_slug_auto_generation_on_creation(self):
        course = create_test_course(title='New Course')
        self.assertIsNotNone(course.slug)
        self.assertIn('new-course', course.slug)

    @patch('django.core.files.storage.default_storage.save')
    def test_image_renaming_on_creation(self, mock_save):
        mock_save.return_value = 'courses/course_1.jpg'

        image_file = SimpleUploadedFile(
            "test_image.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )

        course = Course(
            title='Test Course',
            sub_title='Test subtitle',
            description='Test description',
            price=1000,
            image=image_file
        )
        course.save()

        self.assertIsNotNone(course.pk)

    def test_existing_course_doesnt_reprocess_image(self):
        course = create_test_course()
        original_image = course.image.name

        course.title = 'Updated Title'
        course.save()
        course.refresh_from_db()

        self.assertEqual(course.image.name, original_image)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SectionSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()
        self.course = create_test_course()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_first_section_gets_section_id_1(self):
        section = create_test_section(self.course, title='First Section')
        self.assertEqual(section.section_id, 1)

    def test_subsequent_sections_increment_correctly(self):
        section1 = create_test_section(self.course, title='Section 1')
        section2 = create_test_section(self.course, title='Section 2')
        section3 = create_test_section(self.course, title='Section 3')

        self.assertEqual(section1.section_id, 1)
        self.assertEqual(section2.section_id, 2)
        self.assertEqual(section3.section_id, 3)

    def test_section_id_per_course(self):
        course2 = create_test_course(title='Another Course')

        section1 = create_test_section(self.course, title='Course 1 Section 1')
        section2 = create_test_section(course2, title='Course 2 Section 1')

        self.assertEqual(section1.section_id, 1)
        self.assertEqual(section2.section_id, 1)

    def test_slug_auto_generation(self):
        section = create_test_section(self.course, title='Test Section')
        self.assertIsNotNone(section.slug)
        self.assertIn('test-section', section.slug)

    def test_manual_section_id_preserved_when_set(self):
        section = Section.objects.create(
            section_id=5,
            course_id=self.course,
            title='Manual Section',
        )
        self.assertEqual(section.section_id, 5)


    def test_auto_increment_when_section_id_not_set(self):
        section_1 = Section.objects.create(
            course_id=self.course,
            title='Section 1',
        )
        section_2 = Section.objects.create(
            course_id=self.course,
            title='Section 2',
        )

        self.assertEqual(section_1.section_id, 1)
        self.assertEqual(section_2.section_id, 2)


    def test_manual_and_auto_dont_conflict(self):
        manual = Section.objects.create(
            section_id=5,
            course_id=self.course,
            title='Manual Section',
        )
        auto = Section.objects.create(
            course_id=self.course,
            title='Auto Section',
        )

        self.assertEqual(manual.section_id, 5)
        self.assertEqual(auto.section_id, 6)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class LessonSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()
        self.course = create_test_course()
        self.section = create_test_section(self.course)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_slug_auto_generation(self):
        lesson = create_test_lesson(self.section, title='Test Lesson')
        self.assertIsNotNone(lesson.slug)
        self.assertIn('test-lesson', lesson.slug)

    def test_slug_not_overwritten_on_update(self):
        lesson = create_test_lesson(self.section, title='Original Title')
        original_slug = lesson.slug

        lesson.title = 'Updated Title'
        lesson.save()
        lesson.refresh_from_db()

        self.assertEqual(lesson.slug, original_slug)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomeworkSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_slug_auto_generation(self):
        homework = create_test_homework(self.lesson, title='Test Homework')
        self.assertIsNotNone(homework.slug)
        self.assertIn('test-homework', homework.slug)

    def test_slug_not_overwritten_on_update(self):
        homework = create_test_homework(self.lesson, title='Original Homework')
        original_slug = homework.slug

        homework.title = 'Updated Homework'
        homework.save()
        homework.refresh_from_db()

        self.assertEqual(homework.slug, original_slug)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class UsersHomeworksAttemptsGradeTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.user = create_test_user(email='student@test.com', role='student')
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.homework = create_test_homework(self.lesson)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_grade_returns_none_when_status_not_reviewed(self):
        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='draft'
        )
        self.assertIsNone(attempt.grade)

        attempt.status = 'submitted'
        attempt.save()
        self.assertIsNone(attempt.grade)

    def test_grade_calculation_with_only_task_answers(self):
        task1 = Task.objects.create(
            homework_id=self.homework,
            text='Task 1',
            max_points=10
        )
        task2 = Task.objects.create(
            homework_id=self.homework,
            text='Task 2',
            max_points=10
        )

        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='reviewed'
        )

        Users_tasks_answers.objects.create(
            task_id=task1,
            attempt_id=attempt,
            points=8,
            user_answer='Answer 1',
            status='reviewed'
        )
        Users_tasks_answers.objects.create(
            task_id=task2,
            attempt_id=attempt,
            points=10,
            user_answer='Answer 2',
            status='reviewed'
        )

        grade = attempt.grade
        self.assertEqual(grade, 9)

    def test_grade_calculation_with_only_question_answers(self):
        question1 = Question.objects.create(
            homework_id=self.homework,
            text='Question 1',
            correct_ans='A',
            answer_options=['A', 'B', 'C']
        )
        question2 = Question.objects.create(
            homework_id=self.homework,
            text='Question 2',
            correct_ans='B',
            answer_options=['A', 'B', 'C']
        )

        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='reviewed'
        )

        Users_questions_answers.objects.create(
            question_id=question1,
            attempt_id=attempt,
            user_answer='B',        )
        Users_questions_answers.objects.create(
            question_id=question2,
            attempt_id=attempt,
            user_answer='B',
        )

        grade = attempt.grade
        self.assertEqual(grade, 5)

    def test_grade_calculation_with_mixed_answers(self):
        task = Task.objects.create(
            homework_id=self.homework,
            text='Task',
            max_points=10
        )
        question = Question.objects.create(
            homework_id=self.homework,
            text='Question',
            correct_ans='A',
            answer_options=['A', 'B']
        )

        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='reviewed'
        )

        Users_tasks_answers.objects.create(
            task_id=task,
            attempt_id=attempt,
            points=10,
            user_answer='Answer',
            status='reviewed'
        )
        Users_questions_answers.objects.create(
            question_id=question,
            attempt_id=attempt,
            user_answer='A',
        )

        grade = attempt.grade
        self.assertEqual(grade, 10)

    def test_grade_returns_zero_when_no_points(self):
        task = Task.objects.create(
            homework_id=self.homework,
            text='Task',
            max_points=10
        )

        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='reviewed'
        )

        Users_tasks_answers.objects.create(
            task_id=task,
            attempt_id=attempt,
            points=0,
            user_answer='Wrong answer',
            status='reviewed'
        )

        grade = attempt.grade
        self.assertEqual(grade, 1)

    def test_grade_edge_case_zero_max_points(self):
        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='reviewed'
        )

        grade = attempt.grade
        self.assertEqual(grade, 1)

    def test_grade_only_counts_reviewed_task_answers(self):
        task = Task.objects.create(
            homework_id=self.homework,
            text='Task',
            max_points=10
        )

        attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='reviewed'
        )

        Users_tasks_answers.objects.create(
            task_id=task,
            attempt_id=attempt,
            points=10,
            user_answer='Answer',
            status='submitted'
        )

        grade = attempt.grade
        self.assertEqual(grade, 1)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class UsersTasksAnswersValidationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.user = create_test_user(email='student@test.com', role='student')
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.homework = create_test_homework(self.lesson)
        self.task = Task.objects.create(
            homework_id=self.homework,
            text='Test Task',
            max_points=10
        )
        self.attempt = Users_Homeworks_Attempts.objects.create(
            homework_id=self.homework,
            user_id=self.user,
            status='submitted'
        )

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_validation_passes_when_points_within_limit(self):
        answer = Users_tasks_answers(
            task_id=self.task,
            attempt_id=self.attempt,
            points=10,
            user_answer='Test answer'
        )
        answer.save()
        self.assertEqual(answer.points, 10)

    def test_validation_fails_when_points_exceed_max(self):

        with self.assertRaises(ValidationError) as context:
            Users_tasks_answers.objects.create(
            task_id=self.task,
            attempt_id=self.attempt,
            points=15,
            user_answer='Test answer'
        )

        self.assertIn('points', context.exception.message_dict)

    def test_validation_allows_zero_points(self):
        answer = Users_tasks_answers(
            task_id=self.task,
            attempt_id=self.attempt,
            points=0,
            user_answer='Wrong answer'
        )
        answer.save()
        self.assertEqual(answer.points, 0)

    def test_validation_allows_exact_max_points(self):
        answer = Users_tasks_answers(
            task_id=self.task,
            attempt_id=self.attempt,
            points=10,
            user_answer='Perfect answer'
        )
        answer.save()
        self.assertEqual(answer.points, 10)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PurchasedCourseIsActiveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

        self.user = create_test_user(email='student@test.com', role='student')
        self.course = create_test_course()

        self.payment = Payment.objects.create(
            user=self.user,
            total_sum=1000,
            status='success'
        )

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_is_active_returns_true_when_not_expired(self):
        future_date = timezone.now() + timedelta(days=30)

        purchased = PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=self.payment,
            access_expires_at=future_date
        )

        self.assertTrue(purchased.is_active)

    def test_is_active_returns_false_when_expired(self):
        past_date = timezone.now() - timedelta(days=1)

        purchased = PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=self.payment,
            access_expires_at=past_date
        )

        self.assertFalse(purchased.is_active)

    def test_is_active_edge_case_expires_now(self):
        now = timezone.now()

        purchased = PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=self.payment,
            access_expires_at=now
        )

        self.assertFalse(purchased.is_active)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CoursePriceValidationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_negative_price_fails_validation(self):
        with self.assertRaises(IntegrityError):
            create_test_course(price=-1000)

    def test_overflow_price_fails_validation(self):
        with self.assertRaises(OverflowError):
            create_test_course(
                price=99999999999999999999999999
            )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseLastModifiedByTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch(
            'django.core.files.storage.default_storage._wrapped'
        )
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_last_modified_by_null_on_create(self):
        course = create_test_course()
        self.assertIsNone(course.last_modified_by)

    def test_last_modified_by_set_after_update(self):
        user = create_test_user()
        course = create_test_course()

        course.last_modified_by = user
        course.save()
        course.refresh_from_db()

        self.assertEqual(course.last_modified_by, user)

    def test_last_modified_by_null_after_user_deleted(self):
        user = create_test_user()
        course = create_test_course()
        course.last_modified_by = user
        course.save()

        user.delete()
        course.refresh_from_db()

        self.assertIsNone(course.last_modified_by)
