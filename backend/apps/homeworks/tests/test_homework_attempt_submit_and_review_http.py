from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.cache import caches
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import PurchasedCourse, Question, Task
from apps.courses.tests.test_models import (
    BaseTestCase,
    create_test_course,
    create_test_homework,
    create_test_lesson,
    create_test_section,
    create_test_user,
    publish_course_tree,
)
from apps.homeworks.models import Attempt
from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user


class HomeworkAttemptSubmitAndReviewHttpTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        caches["default"].clear()
        self.client = APIClient()

        self.teacher = create_test_user(email="hw_int_teacher@test.com", role="teacher")
        self.student = create_test_user(email="hw_int_student@test.com", role="student")

        course = create_test_course(title="HW Int Course", sub_title="s", description="d", price=0)
        course.authors.add(self.teacher)

        section = create_test_section(course)
        lesson = create_test_lesson(section)
        self.homework = create_test_homework(lesson, title="HW Integration")

        self.question = Question.objects.create(
            homework=self.homework,
            text="Закрытый вопрос",
            correct_ans="да",
            answer_options=["да", "нет"],
            max_points=3,
        )
        self.task = Task.objects.create(
            homework=self.homework,
            text="Развёрнутое задание",
            max_points=5,
        )

        publish_course_tree(course)

        payment = Payment.objects.create(user=self.student, total_sum=1000, status="success")
        PurchasedCourse.objects.create(
            user=self.student,
            course=course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )

        self.course = course

    def _auth(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    @patch("apps.homeworks.services.review_service.schedule_attempt_reviewed_notification")
    @patch("apps.homeworks.services.attempt_service.build_binding_api")
    def test_student_submits_homework_and_course_author_reviews_attempt(
        self, m_binding, m_schedule
    ):
        m_binding.return_value.sync_many = MagicMock()

        self._auth(self.student)
        base = f"/api/v1/courses/{self.course.slug}/homeworks/{self.homework.slug}"
        draft = self.client.get(f"{base}/attempt/")
        self.assertEqual(draft.status_code, status.HTTP_200_OK)
        attempt_id = draft.data["attempt_id"]

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
                    "user_answer": "ответ",
                },
            ],
        }
        submitted = self.client.post(f"{base}/attempt/submit/", submit_payload, format="json")
        self.assertEqual(submitted.status_code, status.HTTP_201_CREATED)
        self.assertEqual(submitted.data["status"], Attempt.SUBMITTED_STATUS)

        attempt = Attempt.objects.get(attempt_id=attempt_id)
        self.assertEqual(attempt.grade, self.question.max_points)

        task_answer = attempt.task_answers.get(task=self.task)
        review_payload = {
            "attempt_id": str(attempt_id),
            "items": [
                {
                    "task_answer_id": str(task_answer.answer_id),
                    "points": self.task.max_points,
                    "comment": "принято",
                }
            ],
        }

        self._auth(self.teacher)
        reviewed = self.client.post(
            f"/api/v1/courses/{self.course.slug}/attempts/{attempt_id}/review/",
            review_payload,
            format="json",
        )
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        self.assertEqual(reviewed.data["status"], Attempt.REVIEWED_STATUS)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.REVIEWED_STATUS)
        self.assertEqual(attempt.reviewed_by_id, self.teacher.id)
        self.assertEqual(
            attempt.grade,
            self.question.max_points + self.task.max_points,
        )
        m_schedule.assert_called_once()

    def test_open_attempt_requires_course_enrollment(self):
        outsider = create_test_user(email="hw_int_outsider@test.com", role="student")
        self._auth(outsider)
        url = f"/api/v1/courses/{self.course.slug}/homeworks/{self.homework.slug}/attempt/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
