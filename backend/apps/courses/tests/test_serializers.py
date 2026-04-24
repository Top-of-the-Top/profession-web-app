from django.test import TestCase, SimpleTestCase, override_settings
from unittest.mock import patch
import tempfile
from django.utils import timezone
from datetime import timedelta

from ..api.serializers import (
    CourseSerializer,
    CourseDTOSerializer,
    PurchasedCourseSerializer,
    LessonSerializer,
    HomeworkSerializer,
    HomeworkDetailSerializer,
    HomeworkItemsListSerializer,
)
from ..models import Question, Task, PurchasedCourse
from apps.payments.models import Payment
from .test_models import (
    BaseTestCase,
    create_test_user,
    create_test_course,
    create_test_section,
    create_test_lesson,
    create_test_homework,
)


class CourseSerializerUnitTest(SimpleTestCase):

    def test_serializer_has_all_fields(self):
        serializer = CourseSerializer()
        fields = serializer.fields.keys()

        self.assertIn('course_id', fields)
        self.assertIn('title', fields)
        self.assertIn('sub_title', fields)
        self.assertIn('description', fields)
        self.assertIn('price', fields)
        self.assertIn('slug', fields)
        self.assertIn('image_url', fields)

    def test_image_url_is_read_only(self):
        serializer = CourseSerializer()
        self.assertTrue(serializer.fields['image_url'].read_only)

    def test_serializer_validates_required_fields(self):
        data = {}
        serializer = CourseSerializer(data=data)
        self.assertFalse(serializer.is_valid())

        self.assertIn('title', serializer.errors)
        self.assertIn('sub_title', serializer.errors)
        self.assertIn('description', serializer.errors)
        self.assertIn('price', serializer.errors)


class CourseDTOSerializerUnitTest(SimpleTestCase):

    def test_dto_serializer_has_limited_fields(self):
        serializer = CourseDTOSerializer()
        fields = list(serializer.fields.keys())

        expected_fields = ['course_id', 'title', 'sub_title', 'image_url', 'price', 'slug']
        self.assertEqual(sorted(fields), sorted(expected_fields))

    def test_dto_image_url_is_read_only(self):
        serializer = CourseDTOSerializer()
        self.assertTrue(serializer.fields['image_url'].read_only)

class PurchasedCourseSerializerUnitTest(SimpleTestCase):

    def test_serializer_has_nested_course(self):
        serializer = PurchasedCourseSerializer()
        self.assertIn('course', serializer.fields)
        self.assertTrue(serializer.fields['course'].read_only)

    def test_is_active_is_read_only(self):
        serializer = PurchasedCourseSerializer()
        self.assertTrue(serializer.fields['is_active'].read_only)

    def test_serializer_fields(self):
        serializer = PurchasedCourseSerializer()
        fields = list(serializer.fields.keys())

        expected_fields = ['id', 'user', 'course', 'payment', 'access_expires_at', 'is_active']
        self.assertEqual(sorted(fields), sorted(expected_fields))


class LessonSerializerUnitTest(SimpleTestCase):

    def test_serializer_includes_all_fields(self):
        serializer = LessonSerializer()
        self.assertIsNotNone(serializer.fields)


class HomeworkSerializerUnitTest(SimpleTestCase):
    """POST/PATCH: поля модели, без вложенного items."""

    def test_serializer_model_fields_without_items(self):
        serializer = HomeworkSerializer()
        self.assertIsNotNone(serializer.fields)
        self.assertIn('title', serializer.fields)
        self.assertIn('lesson', serializer.fields)
        self.assertNotIn('items', serializer.fields)


class HomeworkDetailSerializerUnitTest(SimpleTestCase):
    """GET: ответ с агрегированным items."""

    def test_serializer_includes_items(self):
        serializer = HomeworkDetailSerializer()
        self.assertIn('items', serializer.fields)


class HomeworkItemsListSerializerUnitTest(SimpleTestCase):

    def test_serializer_has_type_field(self):
        serializer = HomeworkItemsListSerializer()
        self.assertIn('type', serializer.fields)

    def test_serializer_has_required_fields(self):
        serializer = HomeworkItemsListSerializer()
        fields = serializer.fields.keys()
        self.assertIn('type', fields)
        self.assertIn('id', fields)
        self.assertIn('number', fields)
        self.assertIn('text', fields)
        self.assertIn('answer_options', fields)
        self.assertIn('correct_ans', fields)
        self.assertIn('max_points', fields)
        self.assertIn('created_at', fields)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseSerializerIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_serialize_course(self):
        course = create_test_course(
            title='Python Course',
            sub_title='Learn Python',
            description='Complete Python course',
            price=5000
        )

        serializer = CourseSerializer(course)
        data = serializer.data

        self.assertEqual(data['title'], 'Python Course')
        self.assertEqual(data['sub_title'], 'Learn Python')
        self.assertEqual(data['description'], 'Complete Python course')
        self.assertEqual(data['price'], 5000)
        self.assertIn('image_url', data)
        self.assertIn('slug', data)

    def test_deserialize_and_create_course(self):
        data = {
            'title': 'New Course',
            'sub_title': 'New course subtitle',
            'description': 'New course description',
            'price': 10000,
        }

        serializer = CourseSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        course = serializer.save()
        self.assertIsNotNone(course.course_id)
        self.assertEqual(course.title, 'New Course')
        self.assertIsNotNone(course.slug)

    def test_update_course_via_serializer(self):
        course = create_test_course()

        data = {
            'title': 'Updated Title',
            'sub_title': course.sub_title,
            'description': course.description,
            'price': 15000,
        }

        serializer = CourseSerializer(course, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_course = serializer.save()
        self.assertEqual(updated_course.title, 'Updated Title')
        self.assertEqual(updated_course.price, 15000)

    def test_course_with_invalid_price(self):
        data = {
            'title': 'Test Course',
            'sub_title': 'Test subtitle',
            'description': 'Test description',
            'price': -1000,
        }

        serializer = CourseSerializer(data=data)
        self.assertFalse(serializer.is_valid())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseDTOSerializerIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_serialize_course_dto(self):
        course = create_test_course(
            title='Django Course',
            sub_title='Learn Django',
            price=8000
        )

        serializer = CourseDTOSerializer(course)
        data = serializer.data

        self.assertEqual(data['title'], 'Django Course')
        self.assertEqual(data['sub_title'], 'Learn Django')
        self.assertEqual(data['price'], 8000)
        self.assertIn('image_url', data)
        self.assertIn('slug', data)

        self.assertNotIn('description', data)

    def test_serialize_multiple_courses(self):
        course1 = create_test_course(title='Course 1', sub_title='Sub 1', price=1000)
        course2 = create_test_course(title='Course 2', sub_title='Sub 2', price=2000)

        courses = [course1, course2]
        serializer = CourseDTOSerializer(courses, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['title'], 'Course 1')
        self.assertEqual(serializer.data[1]['title'], 'Course 2')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PurchasedCourseSerializerIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()

        self.user = create_test_user(email='student@test.com', role='student')
        self.course = create_test_course()
        self.payment = Payment.objects.create(
            user=self.user,
            total_sum=5000,
            status='success'
        )

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_serialize_purchased_course(self):
        future_date = timezone.now() + timedelta(days=30)
        purchased = PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=self.payment,
            access_expires_at=future_date
        )

        serializer = PurchasedCourseSerializer(purchased)
        data = serializer.data

        self.assertIn('course', data)
        self.assertIn('payment', data)
        self.assertIn('access_expires_at', data)
        self.assertIn('is_active', data)
        self.assertTrue(data['is_active'])

    def test_serialize_expired_purchased_course(self):
        past_date = timezone.now() - timedelta(days=1)
        purchased = PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=self.payment,
            access_expires_at=past_date
        )

        serializer = PurchasedCourseSerializer(purchased)
        data = serializer.data

        self.assertFalse(data['is_active'])

    def test_nested_course_dto_in_purchased(self):
        future_date = timezone.now() + timedelta(days=30)
        purchased = PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=self.payment,
            access_expires_at=future_date
        )

        serializer = PurchasedCourseSerializer(purchased)
        data = serializer.data

        self.assertIn('title', data['course'])
        self.assertIn('price', data['course'])
        self.assertIn('slug', data['course'])
        self.assertNotIn('description', data['course'])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class LessonSerializerIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.course = create_test_course()
        self.section = create_test_section(self.course)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_serialize_lesson(self):
        lesson = create_test_lesson(self.section, title='Lesson 1')

        serializer = LessonSerializer(lesson)
        data = serializer.data

        self.assertEqual(data['title'], 'Lesson 1')
        self.assertIn('slug', data)

    def test_create_lesson_via_serializer(self):
        data = {
            'section': self.section.pk,
            'title': 'New Lesson',
        }

        serializer = LessonSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        lesson = serializer.save()
        self.assertEqual(lesson.title, 'New Lesson')
        self.assertIsNotNone(lesson.slug)

    def test_update_lesson_via_serializer(self):
        lesson = create_test_lesson(self.section, title='Original Lesson')

        data = {'title': 'Updated Lesson'}
        serializer = LessonSerializer(lesson, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated = serializer.save()
        self.assertEqual(updated.title, 'Updated Lesson')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomeworkDetailSerializerIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_serialize_homework(self):
        homework = create_test_homework(self.lesson, title='Homework 1')

        serializer = HomeworkDetailSerializer(homework)
        data = serializer.data

        self.assertEqual(data['title'], 'Homework 1')
        self.assertIn('slug', data)
        self.assertIn('deadline', data)
        self.assertIn('items', data)

    def test_serialize_homework_with_items(self):
        homework = create_test_homework(self.lesson, title='Homework with items')
        Task.objects.create(homework=homework, text='Task 1', max_points=10)
        Question.objects.create(
            homework=homework,
            text='Question 1?',
            correct_ans='A',
            answer_options=['A', 'B', 'C']
        )

        serializer = HomeworkDetailSerializer(homework)
        data = serializer.data

        self.assertEqual(len(data['items']), 2)
        item_types = [item['type'] for item in data['items']]
        self.assertIn('task', item_types)
        self.assertIn('question', item_types)

    def test_items_sorted_by_number_then_created_at(self):
        homework = create_test_homework(self.lesson, title='Homework sorted')
        task1 = Task.objects.create(homework=homework, text='Task 1', max_points=10)
        question1 = Question.objects.create(
            homework=homework,
            text='Question 1?',
            correct_ans='A',
            answer_options=['A', 'B']
        )
        task2 = Task.objects.create(homework=homework, text='Task 2', max_points=15)

        serializer = HomeworkDetailSerializer(homework)
        data = serializer.data

        items = data['items']
        sort_keys = [(item['number'], item['created_at']) for item in items]
        self.assertEqual(sort_keys, sorted(sort_keys))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomeworkSerializerWriteIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_create_homework_via_serializer(self):
        deadline = timezone.now() + timedelta(days=14)
        data = {
            'title': 'New Homework',
            'deadline': deadline.isoformat(),
        }

        serializer = HomeworkSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        homework = serializer.save(lesson=self.lesson)
        self.assertEqual(homework.title, 'New Homework')
        self.assertEqual(homework.lesson_id, self.lesson.lesson_id)
        self.assertEqual(Task.objects.filter(homework=homework).count(), 0)
        self.assertEqual(Question.objects.filter(homework=homework).count(), 0)

    def test_update_homework_title_and_deadline(self):
        homework = create_test_homework(self.lesson, title='Original HW')
        Task.objects.create(homework=homework, text='Existing Task', max_points=10)

        new_deadline = timezone.now() + timedelta(days=21)
        data = {'title': 'Updated Title', 'deadline': new_deadline.isoformat()}

        serializer = HomeworkSerializer(homework, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        updated = serializer.save()
        self.assertEqual(updated.title, 'Updated Title')
        self.assertEqual(Task.objects.filter(homework=homework).count(), 1)
        self.assertTrue(Task.objects.filter(homework=homework, text='Existing Task').exists())
