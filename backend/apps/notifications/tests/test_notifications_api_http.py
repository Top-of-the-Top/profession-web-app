from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import PurchasedCourse
from apps.courses.tests.test_models import create_test_course, create_test_user
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user


class NotificationsApiHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.student = create_test_user(email="api_notes_student@test.com", role="student")
        self.course = create_test_course(title="ApiNotesCourse")
        payment = Payment.objects.create(user=self.student, total_sum=500, status="success")
        PurchasedCourse.objects.create(
            user=self.student,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_list_course_notifications_for_buyer(self):
        n = Notification.objects.create(
            course=self.course,
            title="Обновление",
            notification_type=Notification.COURSE,
            message="Текст курса",
        )
        self._auth(self.student)
        resp = self.client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["has_more"] is False)
        ids = [row["id"] for row in resp.data["results"]]
        self.assertIn(n.id, ids)
        row = next((r for r in resp.data["results"] if r["id"] == n.id))
        self.assertFalse(row["is_read"])

    def test_mark_all_read_sets_flags_on_list(self):
        n = Notification.objects.create(
            course=self.course,
            title="Непрочитанное",
            notification_type=Notification.COURSE,
            message="—",
        )
        self._auth(self.student)
        resp_post = self.client.post("/api/v1/notifications/read-all/")
        self.assertEqual(resp_post.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_post.data["marked"], 1)
        resp = self.client.get("/api/v1/notifications/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        row = next((r for r in resp.data["results"] if r["id"] == n.id))
        self.assertTrue(row["is_read"])

    def test_sse_requires_query_token(self):
        resp = self.client.get("/api/v1/notifications/sse/")
        self.assertEqual(resp.status_code, 401)
