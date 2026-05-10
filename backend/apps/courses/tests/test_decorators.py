import tempfile
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.api.permissions import require_moderator
from apps.courses.api.permissions import require_course_author, require_course_enrollment
from apps.payments.models import Payment

from ..models import Course, CourseEnrollment
from .test_models import BaseTestCase, create_test_course, create_test_user


def create_test_view_with_decorator(decorator, response_data=None):
    if response_data is None:
        response_data = {"status": "ok"}

    @decorator
    def test_view(*args, **kwargs):
        return Response(response_data, status=status.HTTP_200_OK)

    return test_view


def create_mock_user(is_authenticated=True, is_moderator=False, is_teacher=False):
    mock_user = MagicMock()
    mock_user.is_authenticated = is_authenticated
    mock_user.is_moderator.return_value = is_moderator
    mock_user.is_teacher.return_value = is_teacher
    return mock_user


def create_authenticated_request(factory, method="get", path="/test/", user=None):
    request_method = getattr(factory, method)
    request = request_method(path)
    if user:
        request.user = user
        force_authenticate(request, user=user)
    else:
        request.user = None
    return request


class DecoratorIntegrationTestMixin:

    def setUp(self):
        super().setUp()
        self.storage_patcher = patch("django.core.files.storage.default_storage._wrapped")
        self.storage_patcher.start()
        self.factory = APIRequestFactory()
        self._setup_users()

    def tearDown(self):
        super().tearDown()
        self.storage_patcher.stop()

    def _setup_users(self):
        pass

    def assert_decorator_allows_access(self, decorator, user, **kwargs):
        test_view = create_test_view_with_decorator(decorator)
        request = create_authenticated_request(self.factory, user=user)
        response = test_view(request, **kwargs)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def assert_decorator_blocks_access(
        self, decorator, user, expected_status=status.HTTP_403_FORBIDDEN, **kwargs
    ):
        test_view = create_test_view_with_decorator(decorator)
        request = create_authenticated_request(self.factory, user=user)
        response = test_view(request, **kwargs)
        self.assertEqual(response.status_code, expected_status)


class RequireModeratorUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_decorator_allows_moderator(self):
        test_view = create_test_view_with_decorator(require_moderator)
        mock_user = create_mock_user(is_moderator=True)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_decorator_blocks_non_moderator(self):
        test_view = create_test_view_with_decorator(require_moderator)
        mock_user = create_mock_user(is_moderator=False)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)

    def test_decorator_blocks_unauthenticated(self):
        test_view = create_test_view_with_decorator(require_moderator)
        request = create_authenticated_request(self.factory, user=None)
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_decorator_blocks_anonymous_user(self):
        test_view = create_test_view_with_decorator(require_moderator)
        mock_user = create_mock_user(is_authenticated=False)
        request = self.factory.get("/test/")
        request.user = mock_user
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RequireCourseAuthorUnitTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()

    def test_decorator_allows_moderator(self):
        test_view = create_test_view_with_decorator(require_course_author)
        mock_user = create_mock_user(is_moderator=True)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request, course_id=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_decorator_blocks_non_teacher(self):
        course = create_test_course()
        test_view = create_test_view_with_decorator(require_course_author)
        mock_user = create_mock_user(is_moderator=False, is_teacher=False)
        mock_user.is_course_author = MagicMock(return_value=False)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request, course_id=course.course_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_decorator_requires_course_id(self):
        test_view = create_test_view_with_decorator(require_course_author)
        mock_user = create_mock_user(is_moderator=False, is_teacher=True)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decorator_handles_nonexistent_course(self):
        test_view = create_test_view_with_decorator(require_course_author)
        mock_user = create_mock_user(is_moderator=False, is_teacher=True)
        request = create_authenticated_request(self.factory, user=mock_user)
        with patch(
            "apps.courses.api.permissions.Course.objects.get", side_effect=Course.DoesNotExist
        ):
            response = test_view(request, course_id=999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_decorator_blocks_unauthenticated(self):
        test_view = create_test_view_with_decorator(require_course_author)
        request = create_authenticated_request(self.factory, user=None)
        response = test_view(request, course_id=1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RequireCourseEnrollmentUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_decorator_allows_moderator(self):
        test_view = create_test_view_with_decorator(require_course_enrollment)
        mock_user = create_mock_user(is_moderator=True)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request, course_slug="test-slug")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_decorator_requires_course_slug(self):
        test_view = create_test_view_with_decorator(require_course_enrollment)
        mock_user = create_mock_user(is_moderator=False)
        request = create_authenticated_request(self.factory, user=mock_user)
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decorator_handles_nonexistent_course(self):
        test_view = create_test_view_with_decorator(require_course_enrollment)
        mock_user = create_mock_user(is_moderator=False)
        request = create_authenticated_request(self.factory, user=mock_user)
        with patch(
            "apps.courses.api.permissions.Course.objects.get", side_effect=Course.DoesNotExist
        ):
            response = test_view(request, course_slug="nonexistent")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_decorator_blocks_unauthenticated(self):
        test_view = create_test_view_with_decorator(require_course_enrollment)
        request = create_authenticated_request(self.factory, user=None)
        response = test_view(request, course_slug="test-slug")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequireModeratorIntegrationTest(DecoratorIntegrationTestMixin, BaseTestCase):

    def _setup_users(self):
        self.student = create_test_user(email="student@test.com", role="student")
        self.teacher = create_test_user(email="teacher@test.com", role="teacher")
        self.moderator = create_test_user(email="moderator@test.com", role="moderator")

    def test_moderator_can_access(self):
        self.assert_decorator_allows_access(require_moderator, self.moderator)

    def test_teacher_cannot_access(self):
        self.assert_decorator_blocks_access(require_moderator, self.teacher)

    def test_student_cannot_access(self):
        self.assert_decorator_blocks_access(require_moderator, self.student)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequireCourseAuthorIntegrationTest(DecoratorIntegrationTestMixin, BaseTestCase):

    def _setup_users(self):
        self.student = create_test_user(email="student@test.com", role="student")
        self.teacher = create_test_user(email="teacher@test.com", role="teacher")
        self.other_teacher = create_test_user(email="other@test.com", role="teacher")
        self.moderator = create_test_user(email="moderator@test.com", role="moderator")
        self.course = create_test_course()
        self.course.authors.add(self.teacher)

    def test_moderator_can_access_any_course(self):
        self.assert_decorator_allows_access(
            require_course_author, self.moderator, course_id=self.course.course_id
        )

    def test_course_author_can_access(self):
        self.assert_decorator_allows_access(
            require_course_author, self.teacher, course_id=self.course.course_id
        )

    def test_non_author_teacher_cannot_access(self):
        self.assert_decorator_blocks_access(
            require_course_author, self.other_teacher, course_id=self.course.course_id
        )

    def test_student_cannot_access(self):
        self.assert_decorator_blocks_access(
            require_course_author, self.student, course_id=self.course.course_id
        )

    def test_nonexistent_course_returns_404(self):
        self.assert_decorator_blocks_access(
            require_course_author,
            self.teacher,
            expected_status=status.HTTP_404_NOT_FOUND,
            course_id=99999,
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequireCourseEnrollmentIntegrationTest(DecoratorIntegrationTestMixin, BaseTestCase):

    def _setup_users(self):
        self.student = create_test_user(email="student@test.com", role="student")
        self.other_student = create_test_user(email="other@test.com", role="student")
        self.teacher = create_test_user(email="teacher@test.com", role="teacher")
        self.moderator = create_test_user(email="moderator@test.com", role="moderator")
        self.course = create_test_course()
        self.course.authors.add(self.teacher)
        self.payment = Payment.objects.create(user=self.student, total_sum=5000, status="success")
        CourseEnrollment.objects.create(
            user=self.student,
            course=self.course,
            payment=self.payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )

    def test_moderator_can_access_any_course(self):
        self.assert_decorator_allows_access(
            require_course_enrollment, self.moderator, course_slug=self.course.slug
        )

    def test_course_author_can_access(self):
        self.assert_decorator_allows_access(
            require_course_enrollment, self.teacher, course_slug=self.course.slug
        )

    def test_enrolled_student_can_access(self):
        self.assert_decorator_allows_access(
            require_course_enrollment, self.student, course_slug=self.course.slug
        )

    def test_non_enrolled_student_cannot_access(self):
        self.assert_decorator_blocks_access(
            require_course_enrollment, self.other_student, course_slug=self.course.slug
        )

    def test_nonexistent_course_returns_404(self):
        self.assert_decorator_blocks_access(
            require_course_enrollment,
            self.student,
            expected_status=status.HTTP_404_NOT_FOUND,
            course_slug="nonexistent-slug",
        )

    def test_expired_enrollment_blocks_access(self):
        expired_course = create_test_course(title="Expired Course", sub_title="Sub", price=1000)
        payment = Payment.objects.create(user=self.other_student, total_sum=1000, status="success")
        CourseEnrollment.objects.create(
            user=self.other_student,
            course=expired_course,
            payment=payment,
            access_expires_at=timezone.now() - timedelta(days=1),
        )
        self.assert_decorator_blocks_access(
            require_course_enrollment, self.other_student, course_slug=expired_course.slug
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DecoratorEdgeCasesTest(DecoratorIntegrationTestMixin, BaseTestCase):

    def test_require_moderator_with_none_user(self):
        test_view = create_test_view_with_decorator(require_moderator)
        request = create_authenticated_request(self.factory, user=None)
        response = test_view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_require_course_author_with_pk_kwarg(self):
        teacher = create_test_user(email="teacher@test.com", role="teacher")
        course = create_test_course()
        course.authors.add(teacher)
        test_view = create_test_view_with_decorator(require_course_author)
        request = create_authenticated_request(self.factory, user=teacher)
        response = test_view(request, course_slug=course.slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_require_course_enrollment_with_slug_kwarg(self):
        student = create_test_user(email="student@test.com", role="student")
        course = create_test_course()
        payment = Payment.objects.create(user=student, total_sum=5000, status="success")
        CourseEnrollment.objects.create(
            user=student,
            course=course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )
        test_view = create_test_view_with_decorator(require_course_enrollment)
        request = create_authenticated_request(self.factory, user=student)
        response = test_view(request, slug=course.slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_decorators_work_with_viewset_methods(self):
        moderator = create_test_user(email="moderator@test.com", role="moderator")

        class MockViewSet:

            @require_moderator
            def create(self, request):
                return Response({"status": "ok"}, status=status.HTTP_200_OK)

        viewset = MockViewSet()
        request = create_authenticated_request(self.factory, method="post", user=moderator)
        response = viewset.create(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
