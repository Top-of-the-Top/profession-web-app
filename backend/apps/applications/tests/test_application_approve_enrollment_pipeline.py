from datetime import timedelta
from unittest.mock import patch

from django.core.cache import caches
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import CourseEnrollment
from apps.courses.tests.test_models import BaseTestCase, create_test_course, create_test_user
from apps.users.api.utils.token_utils import get_tokens_for_user

from ..models import CourseApplication


class ApplicationApproveEnrollmentPipelineTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        caches["default"].clear()
        self.client = APIClient()
        self.student = create_test_user(email="enroll_pipe_student@test.com", role="student")
        self.teacher = create_test_user(email="enroll_pipe_teacher@test.com", role="teacher")
        self.course = create_test_course(title="Enrollment Pipeline Course", price=0)
        self.course.is_special = True
        self.course.save(update_fields=["is_special"])
        self.course.authors.add(self.teacher)

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_approve_pipeline_creates_active_enrollment_and_course_accessible(self):
        self._auth(self.student)
        self.client.post(f"/api/v1/courses/{self.course.slug}/applications/apply/")

        self._auth(self.teacher)
        r = self.client.get(f"/api/v1/courses/{self.course.slug}/applications/")
        app_id = r.data[0]["application_id"]

        with patch("apps.applications.api.views.dispatcher"):
            self.client.post(f"/api/v1/courses/{self.course.slug}/applications/{app_id}/approve/")

        enrollment = CourseEnrollment.objects.get(user=self.student, course=self.course)
        self.assertEqual(enrollment.source, CourseEnrollment.SOURCE_APPLICATION)
        self.assertIsNone(enrollment.payment)
        self.assertGreater(enrollment.access_expires_at, timezone.now() + timedelta(days=364))
        self.assertTrue(enrollment.is_active)

        self._auth(self.student)
        r = self.client.get("/api/v1/my-courses/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        course_ids = [str(c["course_id"]) for c in r.data]
        self.assertIn(str(self.course.course_id), course_ids)

    def test_approve_pipeline_is_idempotent(self):
        CourseApplication.objects.create(user=self.student, course=self.course)
        app = CourseApplication.objects.get(user=self.student, course=self.course)

        self._auth(self.teacher)
        with patch("apps.applications.api.views.dispatcher"):
            self.client.post(
                f"/api/v1/courses/{self.course.slug}/applications/{app.application_id}/approve/"
            )
            r = self.client.post(
                f"/api/v1/courses/{self.course.slug}/applications/{app.application_id}/approve/"
            )

        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            CourseEnrollment.objects.filter(user=self.student, course=self.course).count(), 1
        )

    def test_reject_pipeline_does_not_create_enrollment(self):
        self._auth(self.student)
        self.client.post(f"/api/v1/courses/{self.course.slug}/applications/apply/")

        self._auth(self.teacher)
        r = self.client.get(f"/api/v1/courses/{self.course.slug}/applications/")
        app_id = r.data[0]["application_id"]

        with patch("apps.applications.api.views.dispatcher"):
            self.client.post(f"/api/v1/courses/{self.course.slug}/applications/{app_id}/reject/")

        self.assertFalse(
            CourseEnrollment.objects.filter(user=self.student, course=self.course).exists()
        )

        self._auth(self.student)
        r = self.client.get("/api/v1/my-courses/")
        course_ids = [str(c["course_id"]) for c in r.data]
        self.assertNotIn(str(self.course.course_id), course_ids)
