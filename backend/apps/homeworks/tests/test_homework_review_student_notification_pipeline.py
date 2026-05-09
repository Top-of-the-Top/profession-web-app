import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core import mail
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import CourseEnrollment, Question, Task
from apps.courses.tests.test_models import (
    create_test_course,
    create_test_homework,
    create_test_lesson,
    create_test_section,
    create_test_user,
    publish_course_tree,
)
from apps.homeworks.models import Attempt
from apps.notifications import tasks as notification_tasks
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user


class HomeworkReviewStudentNotificationPipelineTests(TestCase):

    def setUp(self):
        super().setUp()
        caches["default"].clear()
        self.client = APIClient()
        self._patchers = []
        for path in (
            "apps.notifications.tasks.send_course_notification.delay",
            "apps.notifications.tasks.send_mass_course_email.delay",
            "apps.notifications.tasks.send_personal_notification.delay",
            "apps.notifications.tasks.send_single_email.delay",
            "django.core.files.storage.default_storage",
            "apps.homeworks.services.attempt_service.build_binding_api",
        ):
            p = patch(path)
            self._patchers.append(p)
            mock = p.start()
            if path.endswith("build_binding_api"):
                mock.return_value.sync_many = MagicMock()
            elif path.endswith("send_personal_notification.delay"):
                self.notify_personal_delay = mock
            elif path.endswith("send_single_email.delay"):
                self.notify_single_email_delay = mock

        def _stop_patches():
            for p in reversed(self._patchers):
                p.stop()

        self.addCleanup(_stop_patches)
        uniq = uuid.uuid4().hex[:10]
        self.student_plain_email = f"hw_e2e_student_{uniq}@test.com"
        self.teacher = create_test_user(email=f"hw_e2e_teacher_{uniq}@test.com", role="teacher")
        self.student = create_test_user(email=self.student_plain_email, role="student")
        self.notify_personal_delay.side_effect = (
            lambda uid, title, msg: notification_tasks.send_personal_notification.run(
                uid, title, msg
            )
        )
        self.notify_single_email_delay.side_effect = (
            lambda uid, title, msg: notification_tasks.send_single_email.run(uid, title, msg)
        )
        course = create_test_course(
            title=f"E2E Course {uniq}", sub_title="s", description="d", price=0
        )
        course.authors.add(self.teacher)
        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson, title=f"E2E Homework {uniq}")
        self.question = Question.objects.create(
            homework=self.homework,
            text="Вопрос",
            correct_ans="да",
            answer_options=["да", "нет"],
            max_points=3,
        )
        self.task = Task.objects.create(homework=self.homework, text="Задача", max_points=5)
        publish_course_tree(course)
        payment = Payment.objects.create(user=self.student, total_sum=1000, status="success")
        CourseEnrollment.objects.create(
            user=self.student,
            course=course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )
        self.course = course

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_review_triggers_student_notifications(self):
        self._auth(self.student)
        base = f"/api/v1/courses/{self.course.slug}/homeworks/{self.homework.slug}"
        draft = self.client.get(f"{base}/attempt/")
        self.assertEqual(draft.status_code, status.HTTP_200_OK)
        attempt_id = draft.data["attempt_id"]
        items = draft.data.get("items") or []
        self.assertGreater(len(items), 0)
        submit_payload = {
            "homework_id": str(draft.data["homework_id"]),
            "attempt_id": str(attempt_id),
            "send_at": timezone.now().isoformat(),
            "items": [
                {
                    "type": "question",
                    "id": str(self.question.question_id),
                    "number": 1,
                    "user_answer": "да",
                },
                {
                    "type": "task",
                    "id": str(self.task.task_id),
                    "number": 1,
                    "user_answer": "развёрнутый ответ",
                },
            ],
        }
        submitted = self.client.post(f"{base}/attempt/submit/", submit_payload, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_201_CREATED)
        attempt = Attempt.objects.get(attempt_id=attempt_id)
        task_answer = attempt.task_answers.get(task=self.task)
        expected_final_grade = self.question.max_points + self.task.max_points
        review_payload = {
            "attempt_id": str(attempt_id),
            "items": [
                {
                    "task_answer_id": str(task_answer.answer_id),
                    "points": self.task.max_points,
                    "comment": "зачтено",
                }
            ],
        }
        self.notify_personal_delay.reset_mock()
        self.notify_single_email_delay.reset_mock()
        mail.outbox.clear()
        sse_calls = []

        def capture_publish(*, routing_key, payload):
            sse_calls.append({"routing_key": routing_key, "payload": dict(payload)})

        self._auth(self.teacher)
        with patch("apps.notifications.tasks.publish_event", side_effect=capture_publish):
            with self.captureOnCommitCallbacks(execute=True):
                reviewed = self.client.post(
                    f"/api/v1/courses/{self.course.slug}/attempts/{attempt_id}/review/",
                    review_payload,
                    format="json",
                )
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.REVIEWED_STATUS)
        self.assertEqual(attempt.grade, expected_final_grade)
        self.notify_personal_delay.assert_called_once()
        personal_args = self.notify_personal_delay.call_args[0]
        self.assertEqual(personal_args[0], self.student.id)
        self.assertIn(self.homework.title, personal_args[1])
        self.assertIn(str(expected_final_grade), personal_args[2])
        self.assertIn(str(attempt_id), personal_args[2])
        self.notify_single_email_delay.assert_called_once()
        email_args = self.notify_single_email_delay.call_args[0]
        self.assertEqual(email_args[0], self.student.id)
        user_route = f"user.{self.student.id}"
        user_sse = [x for x in sse_calls if x["routing_key"] == user_route]
        self.assertEqual(len(user_sse), 1)
        payload = user_sse[0]["payload"]
        self.assertEqual(payload["type"], "personal")
        self.assertEqual(payload["notification_type"], Notification.PERSONAL)
        self.assertIn(self.homework.title, payload["title"])
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [self.student_plain_email])
        self.assertIn(self.homework.title, sent.subject)
        self.assertIn(str(expected_final_grade), sent.body)
        self.assertIn(str(attempt_id), sent.body)
        self.assertTrue(
            Notification.objects.filter(
                user_id=self.student.id, notification_type=Notification.PERSONAL
            ).exists()
        )
