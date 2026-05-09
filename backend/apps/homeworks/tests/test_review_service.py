import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.homeworks.models import Attempt, TaskAnswer
from apps.homeworks.services.attempt_service import AttemptService
from apps.homeworks.services.errors import (
    AttemptNotSubmitted,
    ReviewItemNotFound,
    ReviewPointsExceeded,
)
from apps.homeworks.services.review_service import ReviewService, TaskReviewItem
from apps.homeworks.tests.utils import create_homework_bundle, create_student, create_teacher


class ReviewServiceTests(TestCase):

    def setUp(self):
        self.student = create_student()
        self.reviewer = create_teacher()
        self.homework, self.question, self.task = create_homework_bundle()
        self.service = ReviewService()

    def _submit_attempt(self):
        svc = AttemptService()
        attempt = svc.get_or_create_draft(user=self.student, homework=self.homework)
        items = [
            {"type": "question", "id": str(self.question.question_id), "user_answer": "no"},
            {"type": "task", "id": str(self.task.task_id), "user_answer": "answer"},
        ]
        with patch("apps.homeworks.services.attempt_service.build_binding_api") as m_bind:
            m_bind.return_value.sync_many = MagicMock()
            svc.submit(attempt, attempt.attempt_id, timezone.now(), items)
        attempt.refresh_from_db()
        return attempt

    def test_review_not_allowed_for_draft(self):
        svc = AttemptService()
        attempt = svc.get_or_create_draft(user=self.student, homework=self.homework)
        with self.assertRaises(AttemptNotSubmitted):
            self.service.review_attempt(
                attempt=attempt,
                reviewer=self.reviewer,
                items=[TaskReviewItem(task_answer_id=str(uuid.uuid4()), points=0, comment=None)],
            )

    def test_review_unknown_task_answer_raises(self):
        attempt = self._submit_attempt()
        with self.assertRaises(ReviewItemNotFound):
            self.service.review_attempt(
                attempt=attempt,
                reviewer=self.reviewer,
                items=[TaskReviewItem(task_answer_id=str(uuid.uuid4()), points=1, comment=None)],
            )

    def test_review_points_above_task_max_raises(self):
        attempt = self._submit_attempt()
        ta = attempt.task_answers.get(task=self.task)
        with self.assertRaises(ReviewPointsExceeded):
            self.service.review_attempt(
                attempt=attempt,
                reviewer=self.reviewer,
                items=[
                    TaskReviewItem(
                        task_answer_id=str(ta.answer_id),
                        points=self.task.max_points + 1,
                        comment=None,
                    )
                ],
            )

    def test_review_sets_reviewed_status_grade_and_task_correctness(self):
        attempt = self._submit_attempt()
        ta = attempt.task_answers.get(task=self.task)
        auto_grade = attempt.grade
        with patch(
            "apps.homeworks.services.review_service.schedule_attempt_reviewed_notification"
        ) as m_note:
            self.service.review_attempt(
                attempt=attempt,
                reviewer=self.reviewer,
                items=[
                    TaskReviewItem(
                        task_answer_id=str(ta.answer_id), points=self.task.max_points, comment="ok"
                    )
                ],
            )
            m_note.assert_called_once_with(attempt.attempt_id)
        attempt.refresh_from_db()
        ta.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.REVIEWED_STATUS)
        self.assertEqual(attempt.reviewed_by_id, self.reviewer.id)
        self.assertEqual(ta.status, TaskAnswer.CORRECT_STATUS)
        self.assertEqual(attempt.grade, auto_grade + self.task.max_points)

    def test_partial_points_sets_partial_status(self):
        attempt = self._submit_attempt()
        ta = attempt.task_answers.get(task=self.task)
        with patch("apps.homeworks.services.review_service.schedule_attempt_reviewed_notification"):
            self.service.review_attempt(
                attempt=attempt,
                reviewer=self.reviewer,
                items=[TaskReviewItem(task_answer_id=str(ta.answer_id), points=2, comment=None)],
            )
        ta.refresh_from_db()
        self.assertEqual(ta.status, TaskAnswer.PARTIAL_STATUS)
