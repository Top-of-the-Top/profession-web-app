import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.core.meta_management.errors import AssetNotFound
from apps.homeworks.models import Attempt, QuestionAnswer
from apps.homeworks.services.attempt_service import AttemptService
from apps.homeworks.services.errors import (
    AttemptAlreadySubmitted,
    AttemptItemNotFound,
    AttemptPayloadMismatch,
    AttemptValidationError,
)
from apps.homeworks.tests.utils import create_homework_bundle, create_student


class AttemptServiceTests(TestCase):

    def setUp(self):
        self.user = create_student()
        self.homework, self.question, self.task = create_homework_bundle()
        self.service = AttemptService()

    def test_get_or_create_draft_is_idempotent(self):
        first = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        second = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        self.assertEqual(first.pk, second.pk)

    def test_submit_raises_when_payload_attempt_id_mismatches(self):
        attempt = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        with self.assertRaises(AttemptPayloadMismatch):
            self.service.submit(
                attempt, payload_attempt_id=uuid.uuid4(), send_at=timezone.now(), items=[]
            )

    def test_submit_raises_when_already_submitted(self):
        attempt = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        payload_id = attempt.attempt_id
        send_at = timezone.now()
        items = [
            {"type": "question", "id": str(self.question.question_id), "user_answer": "yes"},
            {"type": "task", "id": str(self.task.task_id), "user_answer": ""},
        ]
        with patch("apps.homeworks.services.attempt_service.build_binding_api") as m_bind:
            m_bind.return_value.sync_many = MagicMock()
            self.service.submit(attempt, payload_id, send_at, items)
        with self.assertRaises(AttemptAlreadySubmitted):
            self.service.submit(attempt, payload_id, send_at, items)

    def test_submit_raises_when_item_not_in_attempt(self):
        attempt = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        items = [{"type": "question", "id": str(uuid.uuid4()), "user_answer": "x"}]
        with self.assertRaises(AttemptItemNotFound) as ctx:
            self.service.submit(attempt, attempt.attempt_id, timezone.now(), items)
        self.assertEqual(ctx.exception.details.get("type"), "question")

    def test_submit_raises_when_asset_missing(self):
        attempt = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        asset_id = str(uuid.uuid4())
        items = [
            {
                "type": "task",
                "id": str(self.task.task_id),
                "user_answer": "",
                "asset_ids": [asset_id],
            }
        ]
        with patch("apps.homeworks.services.attempt_service.build_asset_service") as m_factory:
            asset_svc = MagicMock()
            asset_svc.get_asset.side_effect = AssetNotFound()
            m_factory.return_value = asset_svc
            with self.assertRaises(AttemptValidationError) as ctx:
                self.service.submit(attempt, attempt.attempt_id, timezone.now(), items)
        self.assertEqual(ctx.exception.details.get("asset_id"), asset_id)

    def test_submit_marks_submitted_and_sets_grade_from_autocheck(self):
        attempt = self.service.get_or_create_draft(user=self.user, homework=self.homework)
        items = [
            {"type": "question", "id": str(self.question.question_id), "user_answer": "yes"},
            {"type": "task", "id": str(self.task.task_id), "user_answer": "text"},
        ]
        with patch("apps.homeworks.services.attempt_service.build_binding_api") as m_bind:
            m_bind.return_value.sync_many = MagicMock()
            self.service.submit(attempt, attempt.attempt_id, timezone.now(), items)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.SUBMITTED_STATUS)
        self.assertEqual(attempt.grade, self.question.max_points)
        qa = QuestionAnswer.objects.get(attempt=attempt, question=self.question)
        self.assertTrue(qa.is_correct)
