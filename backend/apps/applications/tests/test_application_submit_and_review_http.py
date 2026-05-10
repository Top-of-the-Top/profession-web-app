from datetime import timedelta

from django.core.cache import caches
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import CourseEnrollment
from apps.courses.tests.test_models import BaseTestCase, create_test_course, create_test_user
from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user

from ..models import CourseApplication


def create_special_course(**kwargs):
    course = create_test_course(**kwargs)
    course.is_special = True
    course.save(update_fields=["is_special"])
    return course


def enroll(user, course):
    payment = Payment.objects.create(user=user, total_sum=0, status="success")
    CourseEnrollment.objects.create(
        user=user,
        course=course,
        payment=payment,
        access_expires_at=timezone.now() + timedelta(days=365),
    )


class ApplicationSubmitHttpTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        caches["default"].clear()
        self.client = APIClient()
        self.student = create_test_user(email="submit_http_student@test.com", role="student")
        self.teacher = create_test_user(email="submit_http_teacher@test.com", role="teacher")
        self.course = create_special_course(title="Submit Http Course", price=0)
        self.course.authors.add(self.teacher)

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def _apply_url(self):
        return f"/api/v1/courses/{self.course.slug}/applications/apply/"

    def _my_url(self):
        return f"/api/v1/courses/{self.course.slug}/applications/my/"

    def test_apply_requires_auth(self):
        r = self.client.post(self._apply_url())
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_apply_on_non_special_course_returns_400(self):
        normal_course = create_test_course(title="Normal Course", price=100)
        self._auth(self.student)
        r = self.client.post(f"/api/v1/courses/{normal_course.slug}/applications/apply/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", r.data)

    def test_apply_creates_pending_application(self):
        self._auth(self.student)
        r = self.client.post(self._apply_url())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            CourseApplication.objects.filter(
                user=self.student,
                course=self.course,
                status=CourseApplication.PENDING,
            ).exists()
        )

    def test_apply_twice_returns_409(self):
        self._auth(self.student)
        self.client.post(self._apply_url())
        r = self.client.post(self._apply_url())
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_apply_when_already_enrolled_returns_400(self):
        enroll(self.student, self.course)
        self._auth(self.student)
        r = self.client.post(self._apply_url())
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_pending_application(self):
        CourseApplication.objects.create(user=self.student, course=self.course)
        self._auth(self.student)
        r = self.client.delete(self._my_url())
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            CourseApplication.objects.filter(user=self.student, course=self.course).exists()
        )

    def test_withdraw_nonexistent_application_returns_404(self):
        self._auth(self.student)
        r = self.client.delete(self._my_url())
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_withdraw_reviewed_application_returns_409(self):
        CourseApplication.objects.create(
            user=self.student, course=self.course, status=CourseApplication.APPROVED
        )
        self._auth(self.student)
        r = self.client.delete(self._my_url())
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)


class ApplicationReviewHttpTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        caches["default"].clear()
        self.client = APIClient()
        self.student = create_test_user(email="review_http_student@test.com", role="student")
        self.teacher = create_test_user(email="review_http_teacher@test.com", role="teacher")
        self.moderator = create_test_user(email="review_http_mod@test.com", role="moderator")
        self.course = create_special_course(title="Review Http Course", price=0)
        self.course.authors.add(self.teacher)
        self.application = CourseApplication.objects.create(user=self.student, course=self.course)

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def _list_url(self):
        return f"/api/v1/courses/{self.course.slug}/applications/"

    def _approve_url(self):
        return f"/api/v1/courses/{self.course.slug}/applications/{self.application.application_id}/approve/"

    def _reject_url(self):
        return f"/api/v1/courses/{self.course.slug}/applications/{self.application.application_id}/reject/"

    def test_list_forbidden_for_student(self):
        self._auth(self.student)
        r = self.client.get(self._list_url())
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_applications_for_course_author(self):
        self._auth(self.teacher)
        r = self.client.get(self._list_url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertIn("user", r.data[0])
        self.assertIn("status", r.data[0])

    def test_list_filter_by_status_pending(self):
        other = create_test_user(email="review_http_other@test.com", role="student")
        CourseApplication.objects.create(
            user=other, course=self.course, status=CourseApplication.APPROVED
        )
        self._auth(self.teacher)
        r = self.client.get(self._list_url() + "?status=pending")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["status"], "pending")

    def test_approve_requires_course_author(self):
        self._auth(self.student)
        r = self.client.post(self._approve_url())
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_creates_enrollment_with_application_source(self):
        self._auth(self.teacher)
        r = self.client.post(self._approve_url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "approved")
        enrollment = CourseEnrollment.objects.get(user=self.student, course=self.course)
        self.assertEqual(enrollment.source, CourseEnrollment.SOURCE_APPLICATION)
        self.assertIsNone(enrollment.payment)

    def test_approve_already_reviewed_returns_409(self):
        self.application.status = CourseApplication.APPROVED
        self.application.save(update_fields=["status"])
        self._auth(self.teacher)
        r = self.client.post(self._approve_url())
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_reject_sets_status_and_no_enrollment(self):
        self._auth(self.teacher)
        r = self.client.post(self._reject_url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "rejected")
        self.assertFalse(
            CourseEnrollment.objects.filter(user=self.student, course=self.course).exists()
        )

    def test_reject_already_reviewed_returns_409(self):
        self.application.status = CourseApplication.REJECTED
        self.application.save(update_fields=["status"])
        self._auth(self.teacher)
        r = self.client.post(self._reject_url())
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)

    def test_moderator_can_approve(self):
        self._auth(self.moderator)
        r = self.client.post(self._approve_url())
        self.assertEqual(r.status_code, status.HTTP_200_OK)
