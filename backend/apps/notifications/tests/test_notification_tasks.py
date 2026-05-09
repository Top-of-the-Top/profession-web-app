from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.courses.models import PurchasedCourse
from apps.courses.tests.test_models import create_test_course, create_test_user
from apps.notifications import tasks as notification_tasks
from apps.notifications.models import Notification
from apps.payments.models import Payment


class NotificationTasksPublishPayloadTests(TestCase):
    def test_send_course_notification_persists_and_publishes_course_route(self):
        course = create_test_course(title="NCourse")
        capture = MagicMock()

        with patch("apps.notifications.tasks.publish_event", side_effect=capture):
            notification_tasks.send_course_notification.run(
                course.course_id,
                "Заголовок",
                "Текст",
            )

        self.assertEqual(Notification.objects.count(), 1)
        n = Notification.objects.get()
        self.assertEqual(n.course_id, course.course_id)
        self.assertEqual(n.notification_type, Notification.COURSE)

        capture.assert_called_once()
        kwargs = capture.call_args.kwargs
        self.assertEqual(kwargs["routing_key"], f"course.{course.course_id}")
        payload = kwargs["payload"]
        self.assertEqual(payload["notification_type"], Notification.COURSE)
        self.assertEqual(payload["title"], "Заголовок")
        self.assertEqual(payload["type"], "course_update")

    def test_send_personal_notification_publishes_user_route(self):
        user = create_test_user(email="personal_tasks@test.com", role="student")
        capture = MagicMock()

        with patch("apps.notifications.tasks.publish_event", side_effect=capture):
            notification_tasks.send_personal_notification.run(user.pk, "Привет", "Тело")

        self.assertTrue(
            Notification.objects.filter(
                user_id=user.pk, notification_type=Notification.PERSONAL
            ).exists()
        )
        kwargs = capture.call_args.kwargs
        self.assertEqual(kwargs["routing_key"], f"user.{user.pk}")
        self.assertEqual(kwargs["payload"]["type"], "personal")

    def test_send_system_notification_publishes_system_route(self):
        capture = MagicMock()
        with patch("apps.notifications.tasks.publish_event", side_effect=capture):
            notification_tasks.send_system_notification.run("Система", "Работы")

        n = Notification.objects.get(notification_type=Notification.SYSTEM)
        self.assertIsNone(n.user_id)
        self.assertIsNone(n.course_id)
        self.assertEqual(capture.call_args.kwargs["routing_key"], "system.all")

    def test_send_webinar_scheduled_payload_includes_meta(self):
        course = create_test_course()
        wid = uuid4()
        capture = MagicMock()
        with patch("apps.notifications.tasks.publish_event", side_effect=capture):
            notification_tasks.send_webinar_scheduled_notification.run(
                course.course_id,
                "Тема",
                "Текст",
                wid,
                "cslug",
                "lslug",
                "2026-06-01T18:00:00",
            )

        payload = capture.call_args.kwargs["payload"]
        self.assertEqual(payload["type"], "webinar_scheduled")
        self.assertEqual(payload["webinar_id"], str(wid))


class SendMassCourseEmailTaskTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_mass_course_email_sends_to_each_buyer(self):
        course = create_test_course(title="MassCourse")
        plain_a = "mass_buyer_a@test.com"
        plain_b = "mass_buyer_b@test.com"
        u1 = create_test_user(email=plain_a, role="student")
        u2 = create_test_user(email=plain_b, role="student")
        exp = timezone.now() + timedelta(days=10)
        PurchasedCourse.objects.create(
            user=u1,
            course=course,
            payment=Payment.objects.create(user=u1, total_sum=1, status="success"),
            access_expires_at=exp,
        )
        PurchasedCourse.objects.create(
            user=u2,
            course=course,
            payment=Payment.objects.create(user=u2, total_sum=1, status="success"),
            access_expires_at=exp,
        )

        notification_tasks.send_mass_course_email.run(
            course.course_id, "Тема рассылки", "Общий текст"
        )

        self.assertEqual(len(mail.outbox), 2)
        recipients = {tuple(m.to) for m in mail.outbox}
        self.assertIn((plain_a,), recipients)
        self.assertIn((plain_b,), recipients)
