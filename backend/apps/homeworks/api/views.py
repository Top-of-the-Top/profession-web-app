from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.homeworks.models import TaskReview
from apps.courses.models import Homework
from apps.courses.api.schema import SCHEMA_DETAIL, SCHEMA_VALIDATION
from apps.courses.api.permissions import require_course_author, require_course_enrollment
from apps.homeworks.models import Attempt

from ..services.attempt_service import AttemptService
from ..services.review_service import ReviewService, TaskReviewItem
from ..services.errors import HomeworkServiceError

from .serializers import (
    AttemptSerializer,
    AttemptSubmitSerializer,
    AttemptReviewSerializer,
    ErrorResponseSerializer,
    AttemptListSerializer,
)


HOMEWORK_SLUG_PARAM = OpenApiParameter(
    name='homework_slug',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.PATH,
    required=True,
)

def _error_response(exc):
    payload = {
        'status': 'error',
        'code': exc.code,
        'message': exc.message,
        'details': exc.details or {},
    }

    return Response(payload, status=exc.status)


class HomeworkAttemptView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Получить текущую попытку по домашке',
        description='Возвращает черновик попытки, создаёт если не существует. Требует записи на курс.',
        tags=['Homework'],
        parameters=[
            OpenApiParameter('course_slug', OpenApiTypes.STR, OpenApiParameter.PATH),
            HOMEWORK_SLUG_PARAM,
        ],
        responses={
            200: AttemptSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ErrorResponseSerializer,
        },
    )
    @require_course_enrollment
    def get(self, request, course_slug, homework_slug):
        homework = get_object_or_404(
            Homework,
            slug=homework_slug,
            lesson__section__course__slug=course_slug,
        )
        service = AttemptService()
        try:
            attempt = service.get_or_create_draft(user=request.user, homework=homework)
        except HomeworkServiceError as exc:
            return _error_response(exc)

        return Response(
            AttemptSerializer(attempt, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class HomeworkAttemptListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Список попыток студента по курсу',
        description='Все попытки текущего пользователя по домашкам курса, по убыванию даты.',
        tags=['Home'],
        parameters=[
            OpenApiParameter('course_slug', OpenApiTypes.STR, OpenApiParameter.PATH),
        ],
        responses={
            200: AttemptListSerializer(many=True),
            400: ErrorResponseSerializer,
            401: SCHEMA_DETAIL,
            403: ErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ErrorResponseSerializer,
        },
    )
    @require_course_enrollment
    def get(self, request, course_slug):
        attempts = (
            Attempt.objects
            .filter(
                user=request.user,
                homework__lesson__section__course__slug=course_slug,
            )
            .select_related('homework')
            .prefetch_related('homework__question_set', 'homework__task_set')
            .order_by('-created_at')
        )
        return Response(AttemptListSerializer(attempts, many=True).data, status=status.HTTP_200_OK)

class AttemptDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Получить попытку студента для проверки',
        description=(
            'Возвращает попытку с ответами на все вопросы и задания. '
            'Вопросы (type=question) содержат статус автопроверки. '
            'Задания (type=task) содержат поле **review** — объект с баллами, комментарием '
            'и данными проверяющего, либо **null** если задание ещё не проверено. '
            'Поле **reviewer** внутри review может быть **null** только если учётная '
            'запись проверяющего была удалена из системы. '
            'Доступно только автору курса или модератору.'
        ),
        tags=['Homework'],
        parameters=[
            OpenApiParameter('course_slug', OpenApiTypes.STR, OpenApiParameter.PATH),
            OpenApiParameter('attempt_id', OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        responses={
            200: AttemptSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ErrorResponseSerializer,
        },
    )
    @require_course_author
    def get(self, request, course_slug, attempt_id):
        attempt = get_object_or_404(
            Attempt.objects
            .select_related('homework')
            .prefetch_related(
                'question_answers__question',
                'task_answers__task',
                'task_answers__review__reviewer__profile',
            ),
            attempt_id=attempt_id,
            homework__lesson__section__course__slug=course_slug,
        )
        return Response(
            AttemptSerializer(attempt, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class AttemptReviewView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Выставить ревью попытки (преподаватель)',
        description=(
            'Принимает баллы и комментарий по каждому заданию (Task). '
            'Попытка должна быть в статусе submitted. '
            'Можно перепроверять — update_or_create на каждый TaskReview. '
            'reviewer в ответе равен null только если аккаунт проверяющего удалён.'
        ),
        tags=['Homework'],
        parameters=[
            OpenApiParameter('course_slug', OpenApiTypes.STR, OpenApiParameter.PATH),
            OpenApiParameter('attempt_id', OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        request=AttemptReviewSerializer,
        responses={
            200: AttemptSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            409: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    @require_course_author
    def post(self, request, course_slug, attempt_id):
        attempt = get_object_or_404(
            Attempt.objects.select_related(
                'homework__lesson__section__course'
            ),
            attempt_id=attempt_id,
            homework__lesson__section__course__slug=course_slug,
        )

        serializer = AttemptReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if str(attempt.attempt_id) != str(payload['attempt_id']):
            return Response(
                {
                    'status': 'error',
                    'code': 'ATTEMPT_ID_MISMATCH',
                    'message': 'attempt_id в теле не совпадает с URL.',
                    'details': {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = [
            TaskReviewItem(
                task_answer_id=str(item['task_answer_id']),
                points=item['points'],
                comment=item.get('comment'),
            )
            for item in payload['items']
        ]

        service = ReviewService()
        try:
            attempt = service.review_attempt(
                attempt=attempt,
                reviewer=request.user,
                items=items,
            )
        except HomeworkServiceError as exc:
            return _error_response(exc)

        return Response(
            AttemptSerializer(attempt, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

class HomeworkAttemptSubmitView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Отправить домашку на проверку',
        description='Сохраняет ответы и переводит попытку в статус submitted. Запускает автопроверку вопросов.',
        tags=['Homework'],
        parameters=[
            OpenApiParameter('course_slug', OpenApiTypes.STR, OpenApiParameter.PATH),
            HOMEWORK_SLUG_PARAM,
        ],
        request=AttemptSubmitSerializer,
        responses={
            201: AttemptSerializer,
            400: SCHEMA_VALIDATION,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            409: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
        },
    )
    @require_course_enrollment
    def post(self, request, course_slug, homework_slug):
        homework = get_object_or_404(
            Homework,
            slug=homework_slug,
            lesson__section__course__slug=course_slug,
        )
        serializer = AttemptSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        service = AttemptService()
        try:
            attempt = service.get_or_create_draft(user=request.user, homework=homework)
        except HomeworkServiceError as exc:
            return _error_response(exc)

        try:
            attempt = service.submit(
                attempt=attempt,
                payload_attempt_id=payload['attempt_id'],
                send_at=payload['send_at'],
                items=payload['items'],
            )
        except HomeworkServiceError as exc:
            return _error_response(exc)

        return Response(
            AttemptSerializer(attempt, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

