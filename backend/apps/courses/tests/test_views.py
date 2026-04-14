from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status
import tempfile
from django.utils import timezone
from django.core.cache import caches
from datetime import timedelta

from ..api.views import (
    CourseDTOList,
    CourseListView,
    PurchasedCoursesView,
    course_list_cache_key,
    landing_courses_cache_key,
)
from ..models import Course, Section, Lesson, Homework, Question, Task, PurchasedCourse, Webinar
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

    def test_landing_and_app_course_list_use_distinct_cache_keys(self):
        self.assertNotEqual(landing_courses_cache_key(), course_list_cache_key())


class CourseViewSetUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_list_requires_authentication(self):
        request = self.factory.get('/api/app/courses/')
        view = CourseListView.as_view()

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_moderator_role(self):
        request = self.factory.post('/api/app/courses/', {})
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_moderator.return_value = False
        force_authenticate(request, user=mock_user)

        view = CourseListView.as_view()
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


class MyScheduleViewTest(BaseTestCase, ViewTestMixin):

    def setUp(self):
        super().setUp()
        caches['cold'].clear()
        self.client = APIClient()
        self.teacher = create_test_user(email='teacher_web@test.com', role='teacher')
        self.course = create_test_course(title='Webinar Course')
        self.course.authors.add(self.teacher)
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section, title='Webinar Lesson')
        self.student = self.create_enrolled_student(self.course)

    def test_requires_auth(self):
        response = self.client.get('/api/app/my-schedule/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_sees_webinar_for_enrolled_course(self):
        started = timezone.now() - timedelta(hours=2)
        ended = timezone.now() - timedelta(hours=1)
        Webinar.objects.create(
            lesson=self.lesson,
            status=Webinar.ENDED_STATUS,
            started_at=started,
            ended_at=ended,
        )
        self.authenticate_user(self.student)
        response = self.client.get('/api/app/my-schedule/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row['course_title'], self.course.title)
        self.assertEqual(row['course_slug'], self.course.slug)
        self.assertEqual(row['lesson_title'], self.lesson.title)
        self.assertEqual(row['lesson_slug'], self.lesson.slug)
        self.assertIsNotNone(row['started_at'])
        self.assertIsNotNone(row['ended_at'])

    def test_student_does_not_see_other_course_webinar(self):
        other = create_test_course(title='Other webinar course')
        sec = create_test_section(other)
        les = create_test_lesson(sec)
        Webinar.objects.create(lesson=les, status=Webinar.PENDING_STATUS)
        self.authenticate_user(self.student)
        response = self.client.get('/api/app/my-schedule/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_teacher_sees_webinar_as_author_without_purchase(self):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.PENDING_STATUS)
        solo_teacher = create_test_user(email='solo_teacher@test.com', role='teacher')
        self.course.authors.add(solo_teacher)
        self.authenticate_user(solo_teacher)
        response = self.client.get('/api/app/my-schedule/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['lesson_slug'], self.lesson.slug)


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

    def test_lesson_retrieve(self):
        self.authenticate_user(self.student)
        response = self.client.get(f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Lesson 1')
        self.assertEqual(str(response.data['lesson_id']), str(self.lesson.lesson_id))
        self.assertIn('recording_url', response.data['content'])
        self.assertIn('started_at', response.data['content'])
        self.assertIn('homeworks', response.data['content'])

    def test_lesson_create_as_author(self):
        self.authenticate_user(self.teacher)
        data = {'section': self.section.section_id, 'title': 'New Lesson'}
        response = self.client.post(
            f'/api/courses/{self.course.slug}/lessons/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Lesson')

        new_lesson = Lesson.objects.get(title='New Lesson')
        self.assertEqual(new_lesson.section, self.section)

    def test_lesson_create_rejects_section_from_other_course(self):
        other_course = create_test_course(title='Other course')
        foreign_section = create_test_section(other_course, title='Foreign')

        self.authenticate_user(self.teacher)
        data = {
            'section': str(foreign_section.section_id),
            'title': 'Lesson in wrong section',
        }
        response = self.client.post(
            f'/api/courses/{self.course.slug}/lessons/',
            data,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Lesson.objects.filter(title='Lesson in wrong section').exists())

    def test_lesson_update_as_author(self):
        self.authenticate_user(self.teacher)
        update_data = {'title': 'Updated Lesson'}
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/',
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Lesson')

        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Updated Lesson')

    def test_lesson_delete_as_author(self):
        new_lesson = create_test_lesson(self.section, title='Lesson to Delete')
        initial_count = Lesson.objects.filter(section=self.section).count()

        self.authenticate_user(self.teacher)
        response = self.client.delete(f'/api/courses/{self.course.slug}/lessons/{new_lesson.slug}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Lesson.objects.filter(section=self.section).count(), initial_count - 1)
        self.assertFalse(Lesson.objects.filter(slug=new_lesson.slug).exists())

    def test_lesson_includes_homework_briefs(self):
        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content']['homeworks']), 1)
        hw = response.data['content']['homeworks'][0]
        self.assertEqual(hw['title'], 'HW 1')
        self.assertEqual(hw['homework_slug'], self.homework.slug)
        self.assertEqual(str(hw['homework_id']), str(self.homework.homework_id))
        self.assertIn('deadline', hw)

    def test_homework_list_get_not_allowed(self):
        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_homework_retrieve_with_items(self):
        Task.objects.create(homework=self.homework, text='Task 1', max_points=10)
        Question.objects.create(
            homework=self.homework,
            text='Question 1?',
            correct_ans='A',
            answer_options=['A', 'B', 'C']
        )

        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'HW 1')
        self.assertIn('items', response.data)
        self.assertEqual(len(response.data['items']), 2)

        item_types = [item['type'] for item in response.data['items']]
        self.assertIn('task', item_types)
        self.assertIn('question', item_types)

    def test_homework_create_then_tasks_and_questions_via_separate_endpoints(self):
        self.authenticate_user(self.teacher)
        base = f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/'
        create_data = {
            'title': 'New Homework',
            'deadline': (timezone.now() + timedelta(days=14)).isoformat(),
        }
        response = self.client.post(base, create_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Homework')
        self.assertIn('items', response.data)
        self.assertEqual(len(response.data['items']), 0)

        new_homework = Homework.objects.get(title='New Homework')
        hw_path = f'{base}{new_homework.slug}/'

        r_task = self.client.post(
            f'{hw_path}tasks/',
            {'text': 'Task item', 'max_points': 5},
            format='json',
        )
        self.assertEqual(r_task.status_code, status.HTTP_201_CREATED)

        r_q = self.client.post(
            f'{hw_path}questions/',
            {
                'text': 'Question item?',
                'answer_options': ['A', 'B'],
                'correct_ans': 'A',
            },
            format='json',
        )
        self.assertEqual(r_q.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Task.objects.filter(homework=new_homework).count(), 1)
        self.assertEqual(Question.objects.filter(homework=new_homework).count(), 1)

    def test_homework_patch_title_and_tasks_via_task_endpoints(self):
        old_task = Task.objects.create(homework=self.homework, text='Old Task', max_points=10)

        self.authenticate_user(self.teacher)
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/',
            {'title': 'Updated Homework'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Homework')

        r_patch_task = self.client.patch(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/tasks/{old_task.task_id}/',
            {'text': 'Updated Old Task', 'max_points': 15},
            format='json',
        )
        self.assertEqual(r_patch_task.status_code, status.HTTP_200_OK)

        r_new_task = self.client.post(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/tasks/',
            {'text': 'New Task', 'max_points': 20},
            format='json',
        )
        self.assertEqual(r_new_task.status_code, status.HTTP_201_CREATED)

        self.homework.refresh_from_db()
        self.assertEqual(self.homework.title, 'Updated Homework')
        self.assertEqual(Task.objects.filter(homework=self.homework).count(), 2)
        self.assertTrue(Task.objects.filter(homework=self.homework, task_id=old_task.task_id, text='Updated Old Task').exists())
        self.assertTrue(Task.objects.filter(homework=self.homework, text='New Task').exists())

    def test_homework_delete_task_via_delete_endpoint(self):
        task1 = Task.objects.create(homework=self.homework, text='Task 1', max_points=10)
        task2 = Task.objects.create(homework=self.homework, text='Task 2', max_points=20)

        self.authenticate_user(self.teacher)
        response = self.client.delete(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/tasks/{task2.task_id}/',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Task.objects.filter(homework=self.homework).count(), 1)
        self.assertTrue(Task.objects.filter(task_id=task1.task_id).exists())
        self.assertFalse(Task.objects.filter(task_id=task2.task_id).exists())

    def test_homework_delete(self):
        new_homework = create_test_homework(self.lesson, title='Homework to Delete')
        initial_count = Homework.objects.filter(lesson=self.lesson).count()

        self.authenticate_user(self.teacher)
        response = self.client.delete(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{new_homework.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Homework.objects.filter(lesson=self.lesson).count(), initial_count - 1)
        self.assertFalse(Homework.objects.filter(slug=new_homework.slug).exists())

    def test_homework_items_sorted_by_number_then_created_at(self):
        task1 = Task.objects.create(homework=self.homework, text='Task 1', max_points=10)
        question1 = Question.objects.create(
            homework=self.homework,
            text='Question 1?',
            correct_ans='A',
            answer_options=['A', 'B']
        )
        task2 = Task.objects.create(homework=self.homework, text='Task 2', max_points=15)

        self.authenticate_user(self.student)
        response = self.client.get(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/{self.homework.slug}/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 3)

        items = response.data['items']
        sort_keys = [(item['number'], item['created_at']) for item in items]
        self.assertEqual(sort_keys, sorted(sort_keys))

    def test_non_enrolled_student_cannot_access(self):
        other_student = create_test_user(email='other@test.com', role='student')

        self.assertFalse(
            PurchasedCourse.objects.filter(user=other_student, course=self.course).exists()
        )

        self.authenticate_user(other_student)

        response = self.client.get(f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/homeworks/'
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_author_can_create_and_update(self):
        self.authenticate_user(self.teacher)

        self.assertIn(self.teacher, self.course.authors.all())

        data = {'title': 'Updated Lesson Title'}
        response = self.client.patch(
            f'/api/courses/{self.course.slug}/lessons/{self.lesson.slug}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Lesson Title')

        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Updated Lesson Title')


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
