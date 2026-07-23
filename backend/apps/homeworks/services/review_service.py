from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.homeworks.models import Attempt, TaskAnswer, TaskReview
from apps.homeworks.services.errors import (
    AttemptNotReviewed,
    AttemptNotSubmitted,
    ReviewItemNotFound,
    ReviewPointsExceeded,
    TaskReviewNotFound,
)
from apps.homeworks.services.review_notify import (
    schedule_attempt_review_updated_notification,
    schedule_attempt_reviewed_notification,
)


@dataclass(frozen=True)
class TaskReviewItem:
    task_answer_id: str
    points: int
    comment: str | None


class ReviewService:
    def review_attempt(self, *, attempt: Attempt, reviewer, items: list[TaskReviewItem]) -> Attempt:
        if attempt.status != Attempt.SUBMITTED_STATUS:
            raise AttemptNotSubmitted(
                details={
                    "attempt_id": str(attempt.attempt_id),
                    "status": attempt.status,
                }
            )

        task_answers = {
            str(ta.answer_id): ta for ta in attempt.task_answers.select_related("task").all()
        }

        self._validate_items(items, task_answers)

        with transaction.atomic():
            for item in items:
                ta = task_answers[item.task_answer_id]
                TaskReview.objects.update_or_create(
                    answer=ta,
                    defaults={
                        "reviewer": reviewer,
                        "points": item.points,
                        "comment": item.comment,
                    },
                )
                ta.status = (
                    TaskAnswer.CORRECT_STATUS
                    if item.points >= ta.task.max_points
                    else (
                        TaskAnswer.PARTIAL_STATUS
                        if item.points > 0
                        else TaskAnswer.INCORRECT_STATUS
                    )
                )
                ta.save(update_fields=["status"])

            attempt.grade = self._calculate_total_grade(attempt, items)
            attempt.status = Attempt.REVIEWED_STATUS
            attempt.reviewed_by = reviewer
            attempt.reviewed_at = timezone.now()
            attempt.save(update_fields=["grade", "status", "reviewed_by", "reviewed_at"])

        schedule_attempt_reviewed_notification(attempt.attempt_id)
        attempt.refresh_from_db()
        return attempt

    def update_task_review(
        self,
        *,
        attempt: Attempt,
        task_answer_id: str,
        points: int,
        comment: str | None,
        reviewer,
    ) -> Attempt:
        if attempt.status != Attempt.REVIEWED_STATUS:
            raise AttemptNotReviewed(
                details={"attempt_id": str(attempt.attempt_id), "status": attempt.status}
            )

        ta = attempt.task_answers.select_related("task").filter(answer_id=task_answer_id).first()
        if ta is None:
            raise ReviewItemNotFound(details={"task_answer_id": task_answer_id})

        review = getattr(ta, "review", None)
        if review is None:
            raise TaskReviewNotFound(details={"task_answer_id": task_answer_id})

        if points > ta.task.max_points:
            raise ReviewPointsExceeded(
                details={
                    "task_answer_id": task_answer_id,
                    "points": points,
                    "max_points": ta.task.max_points,
                }
            )

        with transaction.atomic():
            old_points = review.points
            review.points = points
            review.comment = comment
            review.reviewer = reviewer
            review.save(update_fields=["points", "comment", "reviewer", "updated_at"])

            if points >= ta.task.max_points:
                ta.status = TaskAnswer.CORRECT_STATUS
            elif points > 0:
                ta.status = TaskAnswer.PARTIAL_STATUS
            else:
                ta.status = TaskAnswer.INCORRECT_STATUS
            ta.save(update_fields=["status"])

            attempt.grade = (attempt.grade or 0) - old_points + points
            attempt.reviewed_by = reviewer
            attempt.reviewed_at = timezone.now()
            attempt.save(update_fields=["grade", "reviewed_by", "reviewed_at"])

        schedule_attempt_review_updated_notification(attempt.attempt_id)
        attempt.refresh_from_db()
        return attempt

    def _validate_items(self, items: list[TaskReviewItem], task_answers: dict):
        for item in items:
            ta = task_answers.get(item.task_answer_id)
            if ta is None:
                raise ReviewItemNotFound(details={"task_answer_id": item.task_answer_id})
            if item.points > ta.task.max_points:
                raise ReviewPointsExceeded(
                    details={
                        "task_answer_id": item.task_answer_id,
                        "points": item.points,
                        "max_points": ta.task.max_points,
                    }
                )

    def _calculate_total_grade(self, attempt: Attempt, items: list[TaskReviewItem]) -> int:
        auto_grade = attempt.grade or 0
        manual_grade = sum(item.points for item in items)
        return auto_grade + manual_grade
