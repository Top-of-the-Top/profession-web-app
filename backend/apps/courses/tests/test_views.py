from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status
import tempfile
from django.utils import timezone
from datetime import timedelta

from ..api.views import (
    CourseDTOList,
    CourseViewSet,
    PurchasedCoursesView,
    SectionViewSet,
    LessonViewSet,
    HomeworkViewSet,
    TaskViewSet,
    QuestionViewSet,
)
from ..models import Course, Section, Lesson, Homework, Question, Task, PurchasedCourse
from apps.users.models import User
from apps.users.api.utils import encrypt_data, get_tokens_for_user
from apps.payments.models import Payment
from .test_models import (
    BaseTestCase,
    create_test_user,
    create_test_course,
    create_test_section,
    create_test_lesson,
    create_test_homework,
)


class ViewTestMixin:

    def authenticate_user(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access_token"]}')

    def create_enrolled_student(self, course):
        student = create_test_user(email=f'student_{course.course_id}@test.com', role='student')
        payment = Payment.objects.create(user=student, total_sum=5000, status='success')
        PurchasedCourse.objects.create(
            user=student,
            course=course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30)
        )
        return student


class CourseDTOListUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_list_returns_correct_structure(self):
        request = self.factory.get('/api/landing/courses/')
        view = CourseDTOList.as_view()

        mock_user = MagicMock()
        mock_user.purchased_courses.return_value = []
        request.user = mock_user

        with patch.object(CourseDTOList, 'get_queryset', return_value=[]):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('number_of_courses', response.data)
        self.assertIn('data', response.data)


class CourseViewSetUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_list_requires_authentication(self):
        request = self.factory.get('/api/app/courses/')
        view = CourseViewSet.as_view({'get': 'list'})

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_moderator_role(self):
        request = self.factory.post('/api/app/courses/', {})
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_moderator.return_value = False
        force_authenticate(request, user=mock_user)

        view = CourseViewSet.as_view({'post': 'create'})
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CourseViewSetIntegrationTest(BaseTestCase, ViewTestMixin):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.client = APIClient()

        self.student = create_test_user(email='student@test.com', role='student')
        self.teacher = create_test_user(email='teacher@test.com', role='teacher')
        self.moderator = create_test_user(email='moderator@test.com', role='moderator')

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_list_courses_authenticated(self):
        create_test_course(title='Course 1', sub_title='Sub 1', price=1000)
        create_test_course(title='Course 2', sub_title='Sub 2', price=2000)

        self.authenticate_user(self.student)
        response = self.client.get('/api/app/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_retrieve_course_by_slug(self):
        course = create_test_course(title='Test Course', sub_title='Sub', price=5000)

        self.authenticate_user(self.student)
        response = self.client.get(f'/api/app/courses/{course.slug}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Course')

    def test_create_course_as_moderator(self):
        self.authenticate_user(self.moderator)

        data = {
            'title': 'New Course',
            'sub_title': 'New subtitle',
            'description': 'New description',
            'price': 10000,
        }

        response = self.client.post('/api/app/courses/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Course')

    def test_create_course_as_student_forbidden(self):
        self.authenticate_user(self.student)

        data = {
            'title': 'New Course',
            'sub_title': 'New subtitle',
            'description': 'New description',
            'price': 10000,
        }

        response = self.client.post('/api/app/courses/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_course_as_author(self):
        course = create_test_course()
        course.authors.add(self.teacher)

        self.authenticate_user(self.teacher)

        data = {'title': 'Updated Title'}
        response = self.client.patch(f'/api/app/courses/{course.slug}/', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_delete_course_as_moderator(self):
        course = create_test_course()

        self.authenticate_user(self.moderator)
        response = self.client.delete(f'/api/app/courses/{course.slug}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(slug=course.slug).exists())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PurchasedCoursesViewIntegrationTest(BaseTestCase, ViewTestMixin):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.client = APIClient()

        self.user = create_test_user(email='student@test.com', role='student')
        self.course = create_test_course()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_get_purchased_courses(self):
        payment = Payment.objects.create(user=self.user, total_sum=5000, status='success')
        PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30)
        )

        self.authenticate_user(self.user)
        response = self.client.get('/api/app/my-courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['is_active'])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NestedResourcesIntegrationTest(BaseTestCase, ViewTestMixin):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.client = APIClient()

        self.teacher = create_test_user(email='teacher@test.com', role='teacher')
        self.course = create_test_course()
        self.course.authors.add(self.teacher)

        self.student = self.create_enrolled_student(self.course)

        self.section = create_test_section(self.course, title='Section 1')
        self.lesson = create_test_lesson(self.section, title='Lesson 1')
        self.homework = create_test_homework(self.lesson, title='HW 1')

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_section_crud_operations(self):
        initial_section_count = Section.objects.filter(course_id=self.course).count()
        self.assertEqual(initial_section_count, 1)

        self.authenticate_user(self.student)
        response = self.client.get(f'/api/courses/{self.course.slug}/sections/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Section 1')

        response = self.client.get(f'/api/courses/{self.course.slug}/sections/{self.section.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Section 1')
        self.assertEqual(response.data['slug'], self.section.slug)

        self.authenticate_user(self.teacher)
        data = {'course_id': self.course.course_id, 'title': 'New Section'}
        response = self.client.post(f'/api/courses/{self.course.slug}/sections/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Section')

        new_section_count = Section.objects.filter(course_id=self.course).count()
        self.assertEqual(new_section_count, initial_section_count + 1)
        new_section = Section.objects.get(title='New Section')
        self.assertEqual(new_section.course_id, self.course)

        update_data = {'title': 'Updated Section Title'}
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/',
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Section Title')

        self.section.refresh_from_db()
        self.assertEqual(self.section.title, 'Updated Section Title')

        response = self.client.delete(f'/api/courses/{self.course.slug}/sections/{new_section.slug}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        final_section_count = Section.objects.filter(course_id=self.course).count()
        self.assertEqual(final_section_count, initial_section_count)
        self.assertFalse(Section.objects.filter(slug=new_section.slug).exists())

    def test_lesson_crud_operations(self):
        initial_lesson_count = Lesson.objects.filter(section_id=self.section).count()
        self.assertEqual(initial_lesson_count, 1)

        self.authenticate_user(self.student)
        response = self.client.get(f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Lesson 1')

        response = self.client.get(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Lesson 1')
        self.assertEqual(response.data['slug'], self.lesson.slug)

        self.authenticate_user(self.teacher)
        from datetime import date
        data = {'section_id': self.section.section_id, 'title': 'New Lesson', 'date': date.today()}
        response = self.client.post(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Lesson')

        new_lesson_count = Lesson.objects.filter(section_id=self.section).count()
        self.assertEqual(new_lesson_count, initial_lesson_count + 1)
        new_lesson = Lesson.objects.get(title='New Lesson')
        self.assertEqual(new_lesson.section_id, self.section)

        update_data = {'title': 'Updated Lesson'}
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/',
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Lesson')

        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Updated Lesson')

        response = self.client.delete(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{new_lesson.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        final_lesson_count = Lesson.objects.filter(section_id=self.section).count()
        self.assertEqual(final_lesson_count, initial_lesson_count)
        self.assertFalse(Lesson.objects.filter(slug=new_lesson.slug).exists())

    def test_homework_crud_operations(self):
        initial_homework_count = Homework.objects.filter(lesson_id=self.lesson).count()
        self.assertEqual(initial_homework_count, 1)

        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'HW 1')

        response = self.client.get(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'HW 1')
        self.assertEqual(response.data['slug'], self.homework.slug)

        self.authenticate_user(self.teacher)
        data = {
            'lesson_id': self.lesson.lesson_id,
            'title': 'New Homework',
            'deadline': (timezone.now() + timedelta(days=14)).isoformat()
        }
        response = self.client.post(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Homework')

        new_homework_count = Homework.objects.filter(lesson_id=self.lesson).count()
        self.assertEqual(new_homework_count, initial_homework_count + 1)
        new_homework = Homework.objects.get(title='New Homework')
        self.assertEqual(new_homework.lesson_id, self.lesson)

        update_data = {'title': 'Updated Homework'}
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/',
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Homework')

        self.homework.refresh_from_db()
        self.assertEqual(self.homework.title, 'Updated Homework')

        response = self.client.delete(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{new_homework.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        final_homework_count = Homework.objects.filter(lesson_id=self.lesson).count()
        self.assertEqual(final_homework_count, initial_homework_count)
        self.assertFalse(Homework.objects.filter(slug=new_homework.slug).exists())

    def test_task_operations(self):
        initial_task_count = Task.objects.filter(homework_id=self.homework).count()
        task = Task.objects.create(homework_id=self.homework, text='Task 1', max_points=10)

        self.assertEqual(Task.objects.filter(homework_id=self.homework).count(), initial_task_count + 1)

        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/tasks/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], 'Task 1')
        self.assertEqual(response.data[0]['max_points'], 10)

        self.authenticate_user(self.teacher)
        data = {'homework_id': self.homework.homework_id, 'text': 'New Task', 'max_points': 15}
        response = self.client.post(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/tasks/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['text'], 'New Task')

        self.assertEqual(Task.objects.filter(homework_id=self.homework).count(), initial_task_count + 2)
        new_task = Task.objects.get(text='New Task')
        self.assertEqual(new_task.homework_id, self.homework)
        self.assertEqual(new_task.max_points, 15)

    def test_question_operations(self):
        initial_question_count = Question.objects.filter(homework_id=self.homework).count()
        question = Question.objects.create(
            homework_id=self.homework,
            text='Question 1?',
            correct_ans='A',
            answer_options=['A', 'B', 'C']
        )

        self.assertEqual(Question.objects.filter(homework_id=self.homework).count(), initial_question_count + 1)

        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/questions/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['text'], 'Question 1?')
        self.assertEqual(response.data[0]['answer_options'], ['A', 'B', 'C'])

        self.authenticate_user(self.teacher)
        data = {
            'homework_id': self.homework.homework_id,
            'text': 'New Question?',
            'correct_ans': 'B',
            'answer_options': ['A', 'B', 'C', 'D']
        }
        response = self.client.post(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/questions/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['text'], 'New Question?')

        self.assertEqual(Question.objects.filter(homework_id=self.homework).count(), initial_question_count + 2)
        new_question = Question.objects.get(text='New Question?')
        self.assertEqual(new_question.homework_id, self.homework)
        self.assertEqual(new_question.correct_ans, 'B')

    def test_non_enrolled_student_cannot_access(self):
        other_student = create_test_user(email='other@test.com', role='student')

        self.assertFalse(
            PurchasedCourse.objects.filter(user=other_student, course=self.course).exists()
        )

        self.authenticate_user(other_student)

        response = self.client.get(f'/api/courses/{self.course.slug}/sections/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(f'/api/courses/{self.course.slug}/sections/{self.section.slug}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/lessons/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_create_and_update(self):
        self.authenticate_user(self.teacher)

        self.assertIn(self.teacher, self.course.authors.all())

        data = {'title': 'Updated Section'}
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/sections/{self.section.slug}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Section')

        self.section.refresh_from_db()
        self.assertEqual(self.section.title, 'Updated Section')

        new_section = create_test_section(self.course, title='Section to Delete')
        initial_count = Section.objects.filter(course_id=self.course).count()

        response = self.client.delete(f'/api/courses/{self.course.slug}/sections/{new_section.slug}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Section.objects.filter(course_id=self.course).count(), initial_count - 1)
        self.assertFalse(Section.objects.filter(slug=new_section.slug).exists())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RBACIntegrationTest(BaseTestCase, ViewTestMixin):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.client = APIClient()

        self.student = create_test_user(email='student@test.com', role='student')
        self.teacher = create_test_user(email='teacher@test.com', role='teacher')
        self.moderator = create_test_user(email='moderator@test.com', role='moderator')

        self.course = create_test_course()
        self.course.authors.add(self.teacher)

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_student_cannot_create_course(self):
        self.authenticate_user(self.student)
        data = {'title': 'New', 'sub_title': 'Sub', 'description': 'Desc', 'price': 1000}
        response = self.client.post('/api/app/courses/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_modify_others_course(self):
        other_teacher = create_test_user(email='other@test.com', role='teacher')
        self.authenticate_user(other_teacher)

        data = {'title': 'Hacked'}
        response = self.client.patch(f'/api/app/courses/{self.course.slug}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_modify_any_course(self):
        self.authenticate_user(self.moderator)

        data = {'title': 'Moderated'}
        response = self.client.patch(f'/api/app/courses/{self.course.slug}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_access_protected_endpoints(self):
        response = self.client.get('/api/app/courses/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.get('/api/app/my-courses/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class LandingCoursesIntegrationTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch('django.core.files.storage.default_storage._wrapped')
        self.storage_patcher.start()
        self.client = APIClient()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def test_landing_courses_public_access(self):
        create_test_course(title='Course 1', sub_title='Sub 1', price=1000)
        create_test_course(title='Course 2', sub_title='Sub 2', price=2000)

        response = self.client.get('/api/landing/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('number_of_courses', response.data)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['number_of_courses'], 2)
