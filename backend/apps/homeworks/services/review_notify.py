from uuid import UUID

from django.db import transaction

from apps.homeworks.models import Attempt
from apps.notifications.dispatcher import dispatcher
from apps.notifications.events import HomeworkReviewedEvent, HomeworkReviewUpdatedEvent


def schedule_attempt_reviewed_notification(attempt_id: UUID) -> None:

    def _send() -> None:
        attempt = Attempt.objects.select_related("homework").get(attempt_id=attempt_id)
        dispatcher.dispatch(
            HomeworkReviewedEvent(
                user_id=attempt.user_id,
                homework_title=attempt.homework.title,
                grade=attempt.grade,
                attempt_id=attempt.attempt_id,
            )
        )

    transaction.on_commit(_send)


def schedule_attempt_review_updated_notification(attempt_id: UUID) -> None:

    def _send() -> None:
        attempt = Attempt.objects.select_related("homework").get(attempt_id=attempt_id)
        dispatcher.dispatch(
            HomeworkReviewUpdatedEvent(
                user_id=attempt.user_id,
                homework_title=attempt.homework.title,
                grade=attempt.grade,
                attempt_id=attempt.attempt_id,
            )
        )

    transaction.on_commit(_send)
