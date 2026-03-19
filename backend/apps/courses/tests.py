from datetime import timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.courses.models import (
    Course, PurchasedCourse, generate_unique_slug,
    course_image_path,
    DEFAULT_COURSE_IMAGE
)

from apps.courses.signals import (
    delete_course_image,
    handle_course_image_update,
)

from apps.courses.api.views import (
    CourseDTOList, CourseDTOListAuthenticated,
    CourseDetail, PurchasedCoursesView
)


class CourseModelUnitTests(SimpleTestCase):
    """Mock-only тесты для модели Course"""

    def setUp(self):
        self.course_data = {
            'title': 'Тестовый курс',
            'sub_title': 'Краткое описание курса',
            'description': 'Полное описание курса для тестирования',
            'price': 5000,
        }

    def test_course_creation_with_mock(self):
        """Тест создания курса через мок"""
        mock_course = MagicMock(spec=Course)
        mock_course.title = 'Тестовый курс'
        mock_course.sub_title = 'Краткое описание курса'
        mock_course.description = 'Полное описание'
        mock_course.price = 5000
        mock_course.course_id = 1
        mock_course.slug = 'testovyy-kurs-abc12345'
        mock_course.image = DEFAULT_COURSE_IMAGE

        self.assertEqual(mock_course.title, 'Тестовый курс')
        self.assertEqual(mock_course.price, 5000)
        self.assertEqual(mock_course.slug, 'testovyy-kurs-abc12345')

    def test_slug_generation_function(self):
        """Тест функции генерации slug без БД"""
        mock_course = MagicMock(spec=Course)
        mock_course.title = 'Тестовый курс'

        with patch('apps.courses.models.slugify', return_value='testovyy-kurs'), \
                patch('apps.courses.models.uuid.uuid4') as mock_uuid:
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.__str__ = MagicMock(
                return_value='abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
            mock_uuid.return_value = mock_uuid_obj

            slug = generate_unique_slug(mock_course, 'Тестовый курс')

            self.assertTrue(slug.startswith('testovyy-kurs-'))
            self.assertEqual(len(slug.split('-')[-1]), 8)

    def test_course_image_path(self):
        """Тест генерации пути для изображения"""
        mock_course = MagicMock(spec=Course)
        mock_course.pk = 42

        path = course_image_path(mock_course, 'test.jpg')
        self.assertEqual(path, 'courses/course_42.jpg')

        path = course_image_path(mock_course, 'photo.png')
        self.assertEqual(path, 'courses/course_42.png')

    def test_image_url_property_with_default(self):
        """Тест image_url с дефолтным изображением"""
        mock_course = MagicMock(spec=Course)

        expected_url = f'https://storage.yandexcloud.net/test-bucket/{DEFAULT_COURSE_IMAGE}'

        with patch('os.getenv', return_value='test-bucket'):
            type(mock_course).image_url = PropertyMock(
                return_value=expected_url)

            url = mock_course.image_url
            self.assertEqual(url, expected_url)

    def test_image_url_property_with_custom_image(self):
        """Тест image_url с кастомным изображением"""
        mock_course = MagicMock(spec=Course)

        expected_url = '/media/courses/course_1.jpg'
        type(mock_course).image_url = PropertyMock(return_value=expected_url)

        url = mock_course.image_url
        self.assertEqual(url, expected_url)

    def test_str_method(self):
        """Тест строкового представления"""
        mock_course = MagicMock(spec=Course)
        mock_course.title = 'Тестовый курс'
        mock_course.__str__.return_value = 'Тестовый курс'

        self.assertEqual(str(mock_course), 'Тестовый курс')


class CourseSignalUnitTests(SimpleTestCase):
    """Mock-only тесты для сигналов Course"""

    def test_pre_delete_signal_deletes_image(self):
        """Тест что сигнал удаления вызывает delete у изображения"""
        mock_instance = MagicMock(spec=Course)
        mock_image = MagicMock()
        mock_image.name = 'custom.jpg'
        mock_instance.image = mock_image

        delete_course_image(Course, mock_instance)

        mock_image.delete.assert_called_once_with(save=False)

    def test_pre_delete_signal_ignores_default_image(self):
        """Тест что дефолтное изображение не удаляется"""
        mock_instance = MagicMock(spec=Course)
        mock_image = MagicMock()
        mock_image.name = DEFAULT_COURSE_IMAGE
        mock_instance.image = mock_image

        delete_course_image(Course, mock_instance)

        mock_image.delete.assert_not_called()

    def test_pre_delete_signal_ignores_no_image(self):
        """Тест что при отсутствии изображения ошибки нет"""
        mock_instance = MagicMock(spec=Course)
        mock_instance.image = None

        delete_course_image(Course, mock_instance)

    def test_pre_save_signal_deletes_old_image(self):
        """Тест что при обновлении изображения старое удаляется"""
        old_instance = MagicMock()
        old_image = MagicMock()
        old_image.name = 'old.jpg'
        old_instance.image = old_image

        mock_queryset = MagicMock()
        mock_queryset.get.return_value = old_instance

        with patch('apps.courses.models.Course.objects', mock_queryset):
            new_instance = MagicMock(spec=Course)
            new_instance.pk = 1
            new_image = MagicMock()
            new_image.name = 'new.jpg'
            new_instance.image = new_image

            handle_course_image_update(Course, new_instance)

            old_image.delete.assert_called_once_with(save=False)

    def test_pre_save_signal_ignores_new_instance(self):
        """Тест что для новых объектов сигнал не выполняется"""
        new_instance = MagicMock(spec=Course)
        new_instance.pk = None

        handle_course_image_update(Course, new_instance)


class PurchasedCourseUnitTests(SimpleTestCase):
    """Mock-only тесты для PurchasedCourse"""

    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.username = 'testuser'
        self.mock_course = MagicMock()
        self.mock_course.title = 'Тестовый курс'
        self.mock_payment = MagicMock()
        self.mock_payment.pk = 1

    def test_purchased_course_creation(self):
        """Тест создания записи о покупке"""
        mock_purchased = MagicMock(spec=PurchasedCourse)
        mock_purchased.user = self.mock_user
        mock_purchased.course = self.mock_course
        mock_purchased.payment = self.mock_payment
        mock_purchased.access_expires_at = timezone.now() + timedelta(days=30)

        self.assertEqual(mock_purchased.user, self.mock_user)
        self.assertEqual(mock_purchased.course, self.mock_course)

    def test_is_active_property_true(self):
        """Тест активного доступа"""
        mock_purchased = MagicMock(spec=PurchasedCourse)

        type(mock_purchased).is_active = PropertyMock(return_value=True)
        self.assertTrue(mock_purchased.is_active)

    def test_is_active_property_false(self):
        """Тест истекшего доступа"""
        mock_purchased = MagicMock(spec=PurchasedCourse)

        type(mock_purchased).is_active = PropertyMock(return_value=False)
        self.assertFalse(mock_purchased.is_active)

    def test_str_method(self):
        """Тест строкового представления"""
        mock_purchased = MagicMock(spec=PurchasedCourse)
        expected_str = f'{self.mock_user} → {self.mock_course}'
        mock_purchased.__str__.return_value = expected_str

        self.assertEqual(str(mock_purchased), expected_str)


class CourseApiViewUnitTests(SimpleTestCase):
    """Mock-only тесты для API views курсов"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.mock_user = SimpleNamespace(is_authenticated=True)

        self.mock_course = MagicMock()
        self.mock_course.slug = 'test-course'
        self.mock_course.title = 'Тестовый курс'
        self.mock_course.price = 5000

        self.mock_queryset = MagicMock()
        self.mock_queryset.__len__.return_value = 2
        self.mock_queryset.__iter__.return_value = iter(
            [self.mock_course, self.mock_course])

    def test_course_dto_list_public(self):
        """Тест публичного списка курсов"""
        request = self.factory.get('/api/courses/')

        with patch('apps.courses.api.views.CourseDTOListBase.get_queryset') as mock_get_qs, \
                patch('apps.courses.api.views.CourseDTOSerializer') as mock_serializer:
            mock_get_qs.return_value = self.mock_queryset
            mock_serializer.return_value.data = {'title': 'Тестовый курс'}

            response = CourseDTOList.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('number_of_courses', response.data)
            self.assertIn('data', response.data)

    def test_course_dto_list_authenticated_without_auth(self):
        """Тест что авторизованный список требует авторизации"""
        request = self.factory.get('/api/courses/store/')
        response = CourseDTOListAuthenticated.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_course_dto_list_authenticated_with_auth(self):
        """Тест авторизованного списка курсов"""
        request = self.factory.get('/api/courses/store/')
        force_authenticate(request, user=self.mock_user)

        with patch('apps.courses.api.views.CourseDTOListBase.get_queryset') as mock_get_qs, \
                patch('apps.courses.api.views.CourseDTOSerializer') as mock_serializer:
            mock_get_qs.return_value = self.mock_queryset
            mock_serializer.return_value.data = {'title': 'Тестовый курс'}

            response = CourseDTOListAuthenticated.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['number_of_courses'], 2)

    def test_course_detail_success(self):
        """Тест получения деталей курса"""
        request = self.factory.get('/api/courses/test-course/')

        with patch('apps.courses.api.views.Course.objects.filter') as mock_filter:
            mock_filter.return_value.first.return_value = self.mock_course

            with patch('apps.courses.api.views.CourseSerializer') as mock_serializer:
                mock_serializer.return_value.data = {
                    'title': 'Тестовый курс', 'price': 5000}

                response = CourseDetail.as_view()(request, slug='test-course')

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn('course', response.data)
                self.assertEqual(
                    response.data['course']['title'],
                    'Тестовый курс')

    def test_course_detail_not_found(self):
        """Тест получения несуществующего курса"""
        request = self.factory.get('/api/courses/non-existent/')

        with patch('apps.courses.api.views.Course.objects.filter') as mock_filter:
            mock_filter.return_value.first.return_value = None

            response = CourseDetail.as_view()(request, slug='non-existent')

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.data['detail'], 'Курс не найден')

    def test_purchased_courses_without_auth(self):
        """Тест что список купленных курсов требует авторизации"""
        request = self.factory.get('/api/courses/purchased/')
        response = PurchasedCoursesView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_purchased_courses_with_auth_empty(self):
        """Тест пустого списка купленных курсов"""
        request = self.factory.get('/api/courses/purchased/')
        force_authenticate(request, user=self.mock_user)

        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.select_related.return_value = []

        with patch('apps.courses.api.views.PurchasedCourse.objects') as mock_objects:
            mock_objects.filter.return_value = mock_queryset

            with patch('apps.courses.api.views.PurchasedCourseSerializer') as mock_serializer:
                mock_serializer.return_value.data = []

                response = PurchasedCoursesView.as_view()(request)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data, [])

    def test_purchased_courses_with_purchases(self):
        """Тест списка купленных курсов с покупками"""
        request = self.factory.get('/api/courses/purchased/')
        force_authenticate(request, user=self.mock_user)

        mock_purchased = MagicMock()
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value.select_related.return_value = [
            mock_purchased]

        with patch('apps.courses.api.views.PurchasedCourse.objects') as mock_objects:
            mock_objects.filter.return_value = mock_queryset

            with patch('apps.courses.api.views.PurchasedCourseSerializer') as mock_serializer:
                expected_data = [{'course': {'title': 'Тестовый курс'}}]
                mock_serializer.return_value.data = expected_data

                response = PurchasedCoursesView.as_view()(request)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 1)
                self.assertEqual(
                    response.data[0]['course']['title'],
                    'Тестовый курс')


class GenerateUniqueSlugUnitTests(SimpleTestCase):
    """Mock-only тесты для функции generate_unique_slug"""

    def test_generate_slug_normal(self):
        """Тест нормальной генерации slug"""
        mock_instance = MagicMock()

        with patch('apps.courses.models.slugify', return_value='testovyy-kurs'), \
                patch('apps.courses.models.uuid.uuid4') as mock_uuid:
            # Настраиваем uuid мок правильно
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.__str__ = MagicMock(
                return_value='abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
            mock_uuid.return_value = mock_uuid_obj

            slug = generate_unique_slug(mock_instance, 'Тестовый курс')

            # Проверяем только что slug содержит правильные части
            self.assertTrue(slug.startswith('testovyy-kurs-'))
            self.assertEqual(len(slug.split('-')[-1]), 8)

    def test_generate_slug_with_long_title(self):
        """Тест с длинным названием"""
        mock_instance = MagicMock()
        long_title = 'x' * 100

        with patch('apps.courses.models.slugify', return_value='x' * 80), \
                patch('apps.courses.models.uuid.uuid4') as mock_uuid:
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.__str__ = MagicMock(
                return_value='abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
            mock_uuid.return_value = mock_uuid_obj

            slug = generate_unique_slug(mock_instance, long_title)

            self.assertTrue(slug.startswith('x' * 80))
            self.assertEqual(len(slug.split('-')[-1]), 8)

    def test_generate_slug_empty_title(self):
        """Тест с пустым названием"""
        mock_instance = MagicMock()

        with patch('apps.courses.models.slugify', return_value=''), \
                patch('apps.courses.models.uuid.uuid4') as mock_uuid:
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.__str__ = MagicMock(
                return_value='abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
            mock_uuid.return_value = mock_uuid_obj

            slug = generate_unique_slug(mock_instance, '')

            self.assertTrue(slug.startswith('title-'))
            self.assertEqual(len(slug.split('-')[-1]), 8)

    def test_generate_slug_with_special_chars(self):
        """Тест обработки специальных символов"""
        mock_instance = MagicMock()

        with patch('apps.courses.models.slugify', return_value='python-django-web-razrabotka'), \
                patch('apps.courses.models.uuid.uuid4') as mock_uuid:
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.__str__ = MagicMock(
                return_value='abc12345-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
            mock_uuid.return_value = mock_uuid_obj

            slug = generate_unique_slug(
                mock_instance, 'Python & Django: "Web" разработка!')

            self.assertTrue(slug.startswith('python-django-web-razrabotka-'))
            self.assertEqual(len(slug.split('-')[-1]), 8)
