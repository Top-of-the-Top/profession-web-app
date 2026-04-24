from django.test import TestCase
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
import tempfile
from django.db.utils import IntegrityError
from apps.users.models import User
from apps.users.api.utils.crypto_utils import encrypt_data
from apps.payments.models import Payment
from ..models import (
    Course, Section, Lesson, Homework, Question, Task,
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


def create_test_homework(lesson, **kwargs):
    defaults = {
        'lesson': lesson,
        'title': 'Тестовое ДЗ',
        'deadline': timezone.now() + timedelta(days=7),
    }
    defaults.update(kwargs)
    return Homework.objects.create(**defaults)


def publish_course_tree(course):
    course.type = Course.PUBLISHED_STATUS
    course.save(update_fields=['type'])
    for section in course.section_set.all():
        section.type = Section.PUBLISHED_STATUS
        section.save(update_fields=['type'])
        for lesson in section.lesson_set.all():
            lesson.type = Lesson.PUBLISHED_STATUS
            lesson.save(update_fields=['type'])
            for hw in lesson.homework_set.all():
                hw.type = Homework.PUBLISHED_STATUS
                hw.save(update_fields=['type'])


class BaseTestCase(TestCase):
    CELERY_TASKS_TO_MOCK = [
        'apps.courses.signals.send_course_notification.delay',
        'apps.courses.signals.send_course_notification.apply_async',
        'apps.courses.signals.send_personal_notification.delay',
        'apps.courses.signals.send_mass_course_email.delay',
        'apps.courses.signals.send_mass_course_email.apply_async',
        'apps.courses.signals.send_mass_system_email.delay',
        'apps.courses.signals.send_single_email.delay',
    ]

    def setUp(self):
        self.celery_patchers = []
        for task_path in self.CELERY_TASKS_TO_MOCK:
            patcher = patch(task_path)
            patcher.start()
            self.celery_patchers.append(patcher)

        self.storage_patcher = patch('django.core.files.storage.default_storage')
        self.storage_patcher.start()

        self.file_patcher = patch('django.core.files.storage.default_storage')
        self.file_patcher.start()

        self.exists_patcher = patch('django.core.files.storage.default_storage.exists')
        self.exists_patcher.start()

        super().setUp()

    def tearDown(self):
        super().tearDown()
        for patcher in self.celery_patchers:
            patcher.stop()
        self.storage_patcher.stop()
        self.file_patcher.stop()
        self.exists_patcher.stop()


class GenerateUniqueSlugTest(BaseTestCase):

    def test_slug_generation_from_title(self):
        slug = generate_unique_slug('Python для начинающих')

        self.assertIn('python', slug)
        self.assertIn('-', slug)

    def test_slug_generation_with_empty_title(self):
        slug = generate_unique_slug('')

        self.assertIn('title', slug)
        self.assertIn('-', slug)

    def test_slug_generation_with_non_ascii_title(self):
        slug = generate_unique_slug('中文标题')

        self.assertIsNotNone(slug)
        self.assertIn('-', slug)

    def test_slug_has_uuid_part(self):
        slug = generate_unique_slug('Test Title')

        parts = slug.split('-')
        self.assertGreater(len(parts), 1)
        self.assertEqual(len(parts[-1]), 8)

    def test_slug_uniqueness_for_same_title(self):
        slug1 = generate_unique_slug('Same Title')
        slug2 = generate_unique_slug('Same Title')

        self.assertNotEqual(slug1, slug2)

    def test_slug_truncates_long_title(self):
        long_title = 'A' * 100
        slug = generate_unique_slug(long_title)

        self.assertLessEqual(len(slug), 89)

import uuid
class CourseImagePathTest(BaseTestCase):

    def test_image_path_generation_with_jpg(self):
        course = create_test_course()

        path = course_image_path(course, 'test.jpg')

        self.assertIn('courses/course_', path)
        self.assertTrue(path.endswith('.jpg'))
        self.assertTrue(path.startswith('courses/course_'))

    def test_image_path_generation_with_png(self):
        course = Course(course_id=uuid.uuid4(), title='Test Course')
        path = course_image_path(course, 'image.png')
        self.assertTrue(path.startswith('courses/course_'))
        self.assertTrue(path.endswith('.png'))

    def test_image_path_generation_with_uppercase_extension(self):
        course = Course(course_id=uuid.uuid4(), title='Test Course')
        path = course_image_path(course, 'image.PNG')
        self.assertTrue(path.startswith('courses/course_'))
        self.assertTrue(path.endswith('.png'))

    def test_image_path_generation_with_multiple_dots(self):
        course = Course(course_id=uuid.uuid4(), title='Test Course')
        path = course_image_path(course, 'my.image.test.jpg')
        self.assertTrue(path.startswith('courses/course_'))
        self.assertTrue(path.endswith('.jpg'))
class CourseSlugTest(BaseTestCase):

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


class CourseImageUrlTest(BaseTestCase):

    def test_image_url_returns_s3_url_for_default_image(self):
        course = create_test_course()
        url = course.image_url
        self.assertIn('yandexcloud.net', url)

    def test_image_url_contains_bucket_name(self):
        course = create_test_course()
        with patch('os.getenv', return_value='test-bucket'):
            url = course.image_url
            self.assertIn('test-bucket', url)

    @patch('django.core.files.storage.default_storage.url')
    def test_image_path_generation_with_jpg(self, mock_url):
        course = Course.objects.create(title='Test Course', price=5000)
        path = course_image_path(course, 'test.jpg')

        self.assertIn('courses/course', path)
        self.assertTrue(path.startswith('courses/course'))
        self.assertRegex(path, r'^courses/course_')

        uuid_pattern = r'^courses/course_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$'
        self.assertRegex(path, uuid_pattern)


class CourseSaveTest(BaseTestCase):

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


class SectionSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()

    def test_first_section_gets_section_id_1(self):
        section = create_test_section(self.course, title='First Section')
        self.assertEqual(section.section_number, 1)

    def test_subsequent_sections_increment_correctly(self):
        section1 = create_test_section(self.course, title='Section 1')
        section2 = create_test_section(self.course, title='Section 2')
        section3 = create_test_section(self.course, title='Section 3')

        self.assertEqual(section1.section_number, 1)
        self.assertEqual(section2.section_number, 2)
        self.assertEqual(section3.section_number, 3)

    def test_section_id_per_course(self):
        course2 = create_test_course(title='Another Course')

        section1 = create_test_section(self.course, title='Course 1 Section 1')
        section2 = create_test_section(course2, title='Course 2 Section 1')

        self.assertEqual(section1.section_number, 1)
        self.assertEqual(section2.section_number, 1)

    def test_slug_auto_generation(self):
        section = create_test_section(self.course, title='Test Section')
        self.assertIsNotNone(section.slug)
        self.assertIn('test-section', section.slug)

    def test_auto_increment_when_section_id_not_set(self):
        section_1 = Section.objects.create(
            course=self.course,
            title='Section 1',
        )
        section_2 = Section.objects.create(
            course=self.course,
            title='Section 2',
        )

        self.assertEqual(section_1.section_number, 1)
        self.assertEqual(section_2.section_number, 2)


class LessonSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)

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


class HomeworkSaveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

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

class PurchasedCourseIsActiveTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user = create_test_user(email='student@test.com', role='student')
        self.course = create_test_course()

        self.payment = Payment.objects.create(
            user=self.user,
            total_sum=1000,
            status='success'
        )

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


class CoursePriceValidationTest(BaseTestCase):

    def test_negative_price_fails_validation(self):
        with self.assertRaises(IntegrityError):
            create_test_course(price=-1000)

    def test_overflow_price_fails_validation(self):
        with self.assertRaises(OverflowError):
            create_test_course(
                price=99999999999999999999999999
            )


class CourseLastModifiedByTest(BaseTestCase):

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