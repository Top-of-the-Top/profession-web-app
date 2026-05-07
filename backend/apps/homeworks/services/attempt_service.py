from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.meta_management.errors import AssetError, AssetNotFound, AssetPermissionDenied
from apps.core.meta_management.factory import build_asset_service, build_binding_api
from apps.core.models import AssetStatus
from apps.homeworks.models import Attempt, QuestionAnswer, TaskAnswer
from apps.homeworks.services.autocheck_service import AutocheckService
from apps.homeworks.services.errors import (
    AttemptAlreadySubmitted,
    AttemptItemNotFound,
    AttemptPayloadMismatch,
    AttemptValidationError,
)


@dataclass(frozen=True)
class SubmitItem:
    type: str
    target_id: str
    user_answer: str
    asset_ids: list = field(default_factory=list)


class AttemptService:
    def __init__(self, autocheck_service=None):
        self.autocheck_service = autocheck_service or AutocheckService()

    def get_or_create_draft(self, *, user, homework):
        with transaction.atomic():
            attempt = (
                Attempt.objects
                .select_for_update()
                .filter(user=user, homework=homework)
                .first()
            )
            if attempt is not None:
                return attempt

            attempt = Attempt.objects.create(
                user=user,
                homework=homework,
                status=Attempt.DRAFT_STATUS,
            )
            self._prefill_answers(attempt)
            return attempt

    def submit(self, attempt, payload_attempt_id, send_at, items):
        if str(attempt.attempt_id) != str(payload_attempt_id):
            raise AttemptPayloadMismatch()

        if attempt.status != Attempt.DRAFT_STATUS:
            raise AttemptAlreadySubmitted(
                details={'attempt_id': str(attempt.attempt_id), 'status': attempt.status},
            )

        normalized = [self._normalize_item(item) for item in items]

        self._preflight_assets(normalized, owner=attempt.user)

        with transaction.atomic():
            self._apply_items(attempt, normalized)
            self.autocheck_service.run(attempt)
            attempt.status = Attempt.SUBMITTED_STATUS
            attempt.send_at = send_at or timezone.now()
            attempt.grade = self._calculate_grade(attempt)
            attempt.save(update_fields=['status', 'send_at', 'grade'])

        attempt.refresh_from_db()
        return attempt

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _prefill_answers(self, attempt):
        homework = attempt.homework
        QuestionAnswer.objects.bulk_create([
            QuestionAnswer(attempt=attempt, question=q, user_answer='')
            for q in homework.question_set.all()
        ])
        TaskAnswer.objects.bulk_create([
            TaskAnswer(attempt=attempt, task=t, user_answer='')
            for t in homework.task_set.all()
        ])

    def _normalize_item(self, item):
        return SubmitItem(
            type=item['type'],
            target_id=str(item['id']),
            user_answer=item.get('user_answer') or '',
            asset_ids=[str(x) for x in (item.get('asset_ids') or []) if x],
        )

    def _preflight_assets(self, items, owner):
 
        asset_service = build_asset_service()

        for item in items:
            if item.type != 'task' or not item.asset_ids:
                continue

            for asset_id in item.asset_ids:
                try:
                    asset = asset_service.get_asset(asset_id)
                except AssetNotFound as e:
                    raise AttemptValidationError(
                        message='Файл не найден.',
                        details={'asset_id': asset_id},
                    ) from e

                if str(asset.owner_id) != str(owner.pk):
                    raise AttemptValidationError(
                        message='Файл не принадлежит текущему пользователю.',
                        details={'asset_id': asset_id},
                    )

                if asset.status == AssetStatus.PENDING:
                    try:
                        asset_service.commit_asset(asset.asset_id)
                    except AssetError:
                        raise AttemptValidationError(
                            message='Файл ещё не загружен. Дождитесь завершения загрузки.',
                            details={'asset_id': asset_id},
                        )

                elif asset.status == AssetStatus.DELETED:
                    raise AttemptValidationError(
                        message='Файл был удалён и недоступен.',
                        details={'asset_id': asset_id},
                    )

    def _apply_items(self, attempt, items):
        question_by_id = {str(qa.question_id): qa for qa in attempt.question_answers.all()}
        task_by_id = {str(ta.task_id): ta for ta in attempt.task_answers.all()}

        binding = build_binding_api()

        for item in items:
            if item.type == 'question':
                qa = question_by_id.get(item.target_id)
                if qa is None:
                    raise AttemptItemNotFound(
                        details={'type': 'question', 'id': item.target_id},
                    )
                QuestionAnswer.objects.filter(pk=qa.pk).update(user_answer=item.user_answer)

            elif item.type == 'task':
                ta = task_by_id.get(item.target_id)
                if ta is None:
                    raise AttemptItemNotFound(
                        details={'type': 'task', 'id': item.target_id},
                    )
                TaskAnswer.objects.filter(pk=ta.pk).update(user_answer=item.user_answer)

                if item.asset_ids:
                    try:
                        binding.sync_many(
                            content_object=ta,
                            role='task_attachment',
                            asset_ids=item.asset_ids,
                            owner=attempt.user,
                        )
                    except AssetError as e:
                        raise AttemptValidationError(
                            message=e.message,
                            details={'type': 'task', 'id': item.target_id, **e.details},
                        ) from e

    def _calculate_grade(self, attempt):
        return (
            attempt.question_answers
            .filter(is_correct=True)
            .aggregate(total=Sum('question__max_points'))['total']
            or 0
        )
