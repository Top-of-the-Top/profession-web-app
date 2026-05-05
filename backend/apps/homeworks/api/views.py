from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Homework
from apps.courses.api.schema import SCHEMA_DETAIL, SCHEMA_VALIDATION
from apps.homeworks.models import Attempt

from ..services.attempt_service import AttemptService
from ..services.errors import HomeworkServiceError

from .serializers import (
    AttemptSerializer,
    AttemptSubmitSerializer,
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
        description=(
            '**404**: домашка с таким slug не найдена (стандартный ответ DRF с полем detail). '
            'Ошибки сервиса — тело вида ErrorResponse (**status**, **code**, **message**, **details**).'
        ),
        tags=['Homework'],
        parameters=[HOMEWORK_SLUG_PARAM],
        responses={
            200: AttemptSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request, homework_slug):
        homework = get_object_or_404(Homework, slug=homework_slug)

        service = AttemptService()
        try:
            attempt = service.get_or_create_draft(user=request.user, homework=homework)
        except HomeworkServiceError as exc:
            return _error_response(exc)

        data = AttemptSerializer(attempt, context={'request': request}).data
        return Response(data, status=status.HTTP_200_OK)

class HomeworkAttemptListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Получить список текущих домашек',
        tags=['Home'],
        responses={
            200: AttemptListSerializer(many=True),
            401: SCHEMA_DETAIL,
        },
    )
    def get(self, request):
        user = request.user
        attempts = (
            Attempt.objects
            .filter(user=user)
            .select_related('homework')
            .prefetch_related('homework__question_set', 'homework__task_set')
            .order_by('-created_at')
        )
        data = AttemptListSerializer(attempts, many=True).data

        return Response(data, status=status.HTTP_200_OK)

class HomeworkAttemptSubmitView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Отправить домашку на проверку',
        description=(
            '**400**: либо ошибки валидации тела (**AttemptSubmitSerializer**, формат полей DRF), '
            'либо ошибка сервиса в форме ErrorResponse. **404**: домашка не найдена.'
        ),
        tags=['Homework'],
        parameters=[HOMEWORK_SLUG_PARAM],
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
    def post(self, request, homework_slug):
        homework = get_object_or_404(Homework, slug=homework_slug)

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

        data = AttemptSerializer(attempt, context={'request': request}).data
        return Response(data, status=status.HTTP_201_CREATED)

