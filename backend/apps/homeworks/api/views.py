import re
from apps.core.services.presigned_url import PresignedUrlService
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from uuid import uuid4

from apps.courses.models import Homework
from apps.homeworks.models import Attempt

from ..services import (
    AttemptAlreadySubmitted,
    AttemptItemNotFound,
    AttemptPayloadMismatch,
    AttemptService,
    AttemptValidationError,
    HomeworkServiceError,
    StorageUnavailable,
    UploadFileTooLarge,
)
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


SERVICE_ERROR_STATUS_MAP = {
    AttemptAlreadySubmitted: status.HTTP_409_CONFLICT,
    AttemptItemNotFound: status.HTTP_400_BAD_REQUEST,
    AttemptPayloadMismatch: status.HTTP_400_BAD_REQUEST,
    AttemptValidationError: status.HTTP_400_BAD_REQUEST,
    UploadFileTooLarge: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    StorageUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _error_response(exc, http_status=None):
    payload = {
        'status': 'error',
        'code': exc.code,
        'message': exc.message,
        'details': exc.details or {},
    }
    if http_status is None:
        http_status = SERVICE_ERROR_STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return Response(payload, status=http_status)


class HomeworkAttemptView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Получить текущую попытку по домашке',
        tags=['Homework'],
        parameters=[HOMEWORK_SLUG_PARAM],
        responses={
            200: AttemptSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
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
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
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
        try:
            data = AttemptListSerializer(attempts, many=True).data
        except Exception as exc:
            return _error_response(exc)

        return Response(data, status=status.HTTP_200_OK)

class HomeworkAttemptSubmitView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Отправить домашку на проверку',
        tags=['Homework'],
        parameters=[HOMEWORK_SLUG_PARAM],
        request=AttemptSubmitSerializer,
        responses={
            201: AttemptSerializer,
            400: ErrorResponseSerializer,
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
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

class UploadFileAttachmentView(APIView):
    permission_classes = (IsAuthenticated, )
    
    @extend_schema(
        summary='Загрузить файл в хранилище',
        tags=['Homework'],
        parameters=[HOMEWORK_SLUG_PARAM],
        request=UploadFileRequestSerializer,
        responses={
            201: S3UploadResponseSerializer,
            400: OpenApiTypes.OBJECT, 
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            413: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request, homework_slug):
        serializer = UploadFileRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                AttemptValidationError(details=serializer.errors)
            )

        payload = serializer.validated_data

        if payload['file_size'] > 10 * 1024 * 1024:
            return _error_response(UploadFileTooLarge())

        unique_id = uuid4().hex[:8]
        filepath = (
            f"homeworks/{homework_slug}/"
            f"task_{payload['task_id']}/"
            f"attempt_{payload['attempt_id']}/"
            f"{unique_id}_{payload['file_name']}.{payload['file_extension']}"
        )

        presigned_url_service = PresignedUrlService()
        data = presigned_url_service.get_presigned_url_response(filepath)

        if not data:
            return _error_response(StorageUnavailable())

        data['method'] = 'POST'

        return Response(data=data, status=status.HTTP_201_CREATED)