import uuid
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from apps.courses.tests.test_models import create_test_user
from apps.notifications.dispatcher import dispatcher
from apps.notifications.events import HomeworkReviewedEvent
from apps.notifications.models import Notification


class HomeworkReviewedDispatchPipelineTests(TestCase):

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        FRONTEND_HOST="https://learn.example",
    )
    def test_dispatch_homework_reviewed_personal_mail_and_publish_payload(self):
        uniq = uuid.uuid4().hex[:8]
        plain = f"dispatch_pipeline_{uniq}@test.com"
        student = create_test_user(email=plain, role="student")
        attempt_id = uuid.uuid4()
        sse_calls = []

        def capture_publish(*, routing_key, payload):
            sse_calls.append({"routing_key": routing_key, "payload": dict(payload)})

        mail.outbox.clear()
        with patch("apps.notifications.tasks.publish_event", side_effect=capture_publish):
            dispatcher.dispatch(
                HomeworkReviewedEvent(
                    user_id=student.pk,
                    homework_title="Контрольная",
                    grade=9,
                    attempt_id=attempt_id,
                    with_email=True,
                )
            )
        self.assertTrue(
            Notification.objects.filter(
                user_id=student.pk, notification_type=Notification.PERSONAL
            ).exists()
        )
        user_route = f"user.{student.pk}"
        personal_sse = [x for x in sse_calls if x["routing_key"] == user_route]
        self.assertEqual(len(personal_sse), 1)
        self.assertEqual(personal_sse[0]["payload"]["type"], "personal")
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [plain])
        self.assertIn("Контрольная", sent.subject)
        self.assertIn("9", sent.body)
        self.assertIn(str(attempt_id), sent.body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_dispatch_without_email_skips_single_email_task_output(self):
        student = create_test_user(email="no_mail@test.com", role="student")
        mail.outbox.clear()
        with patch("apps.notifications.tasks.publish_event"):
            dispatcher.dispatch(
                HomeworkReviewedEvent(
                    user_id=student.pk,
                    homework_title="Без письма",
                    grade=None,
                    attempt_id=uuid.uuid4(),
                    with_email=False,
                )
            )
        self.assertEqual(len(mail.outbox), 0)
