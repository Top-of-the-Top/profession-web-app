from dataclasses import dataclass
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import Attempt, QuestionAnswer, TaskAnswer

from apps.core.services.errors import AssetError
from apps.core.services.factory import build_binding_api

class HomeworkServiceError(Exception):
    code = 'HOMEWORK_ERROR'
    message = 'Ошибка обработки домашнего задания.'

    def __init__(self, message=None, *, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}


class AttemptAlreadySubmitted(HomeworkServiceError):
    code = 'ATTEMPT_ALREADY_SUBMITTED'
    message = 'Попытка уже отправлена на проверку.'


class AttemptItemNotFound(HomeworkServiceError):
    code = 'ATTEMPT_ITEM_NOT_FOUND'
    message = 'Элемент не принадлежит текущей попытке.'


class AttemptPayloadMismatch(HomeworkServiceError):
    code = 'ATTEMPT_PAYLOAD_MISMATCH'
    message = 'Переданный attempt_id не совпадает с текущей попыткой.'


class AttemptValidationError(HomeworkServiceError):
    code = 'VALIDATION_ERROR'
    message = 'Ошибка в данных запроса.'


class UploadFileTooLarge(HomeworkServiceError):
    code = 'FILE_TOO_LARGE'
    message = 'Файл больше 10 МБ.'


class StorageUnavailable(HomeworkServiceError):
    code = 'STORAGE_ERROR'
    message = 'Не удалось связаться с облачным хранилищем.'

@dataclass(frozen=True)
class SubmitItem:
    type: str
    target_id: str
    user_answer: str
    asset_ids: list


class AutocheckService:

    def run(self, attempt):
        question_answers = attempt.question_answers.select_related('question')

        for qa in question_answers:
            is_correct = bool(qa.user_answer) and qa.user_answer == qa.question.correct_ans
            new_status = (
                QuestionAnswer.CORRECT_STATUS
                if is_correct
                else QuestionAnswer.INCORRECT_STATUS
            )
            QuestionAnswer.objects.filter(pk=qa.pk).update(
                status=new_status,
                is_correct=is_correct,
            )


class AttemptService:
    def __init__(self, autocheck_service=None):
        self.autocheck_service = autocheck_service or AutocheckService()

    @transaction.atomic
    def get_or_create_draft(self, *, user, homework):
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

    @transaction.atomic
    def submit(self, attempt, payload_attempt_id, send_at, items):
        if str(attempt.attempt_id) != str(payload_attempt_id):
            raise AttemptPayloadMismatch()

        if attempt.status != Attempt.DRAFT_STATUS:
            raise AttemptAlreadySubmitted(
                details={'attempt_id': str(attempt.attempt_id), 'status': attempt.status},
            )

        normalized = [self._normalize_item(item) for item in items]
        self._apply_items(attempt, normalized)

        self.autocheck_service.run(attempt)

        attempt.status = Attempt.SUBMITTED_STATUS
        attempt.send_at = send_at or timezone.now()
        attempt.grade = self._calculate_grade(attempt)
        attempt.save(update_fields=['status', 'send_at', 'grade'])

        attempt.refresh_from_db()
        return attempt

    def _prefill_answers(self, attempt):
        homework = attempt.homework

        QuestionAnswer.objects.bulk_create([
            QuestionAnswer(attempt=attempt, question=question, user_answer='')
            for question in homework.question_set.all()
        ])
        TaskAnswer.objects.bulk_create([
            TaskAnswer(attempt=attempt, task=task, user_answer='')
            for task in homework.task_set.all()
        ])

    def _normalize_item(self, item):
        asset_ids = [str(x) for x in (item.get('asset_ids') or []) if x]
        return SubmitItem(
            type=item['type'],
            target_id=str(item['id']),
            user_answer=item.get('user_answer') or '',
            asset_ids=asset_ids,
        )

    def _apply_items(self, attempt, items):
        question_by_id = {}
        for qu in attempt.question_answers.all():
            question_by_id[str(qu.question_id)] = qu

        task_by_id = {}
        for ta in attempt.task_answers.all():
            task_by_id[str(ta.task_id)] = ta

        binding = build_binding_api()

        for item in items:
            if item.type == "question":
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
        correct_points = (
            attempt.question_answers
            .filter(is_correct=True)
            .aggregate(total=Sum('question__max_points'))['total']
            or 0
        )
        return correct_points
