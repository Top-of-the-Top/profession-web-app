from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..meta_management.errors import AssetError
from ..meta_management.factory import build_upload_api
from ..processors.error_processor import process_error_response
from .serializers import (
    AssetErrorResponseSerializer,
    InitiateUploadRequestSerializer,
    InitiateUploadResponseSerializer,
    UploadStatusResponseSerializer,
)


class AssetUploadInitiateView(APIView):
    permission_classes = (IsAuthenticated,)
    upload_api = None

    def _get_upload_api(self):
        return self.upload_api or build_upload_api()

    @extend_schema(
        summary='Инициировать загрузку файла',
        tags=['Assets'],
        request=InitiateUploadRequestSerializer,
        responses={
            201: InitiateUploadResponseSerializer,
            200: InitiateUploadResponseSerializer,
            400: AssetErrorResponseSerializer,
            401: AssetErrorResponseSerializer,
            403: AssetErrorResponseSerializer,
            503: AssetErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = InitiateUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            result = self._get_upload_api().initiate_upload(
                user=request.user,
                intent=payload['intent'],
                filename=payload['filename'],
                mime_type=payload['mime_type'],
                size=payload['size'],
                sha256=payload.get('sha256', ''),
            )
        except AssetError as exc:
            return process_error_response(exc)

        data = InitiateUploadResponseSerializer(result).data
        http_status = status.HTTP_200_OK if result.dedup else status.HTTP_201_CREATED
        return Response(data, status=http_status)


class AssetUploadStatusView(APIView):
    permission_classes = (IsAuthenticated,)
    upload_api = None

    def _get_upload_api(self):
        return self.upload_api or build_upload_api()

    @extend_schema(
        summary='Статус загрузки ассета',
        tags=['Assets'],
        responses={
            200: UploadStatusResponseSerializer,
            401: AssetErrorResponseSerializer,
            403: AssetErrorResponseSerializer,
            404: AssetErrorResponseSerializer,
        },
    )
    def get(self, request, asset_id):
        try:
            asset = self._get_upload_api().get_upload_status(
                user=request.user,
                asset_id=asset_id,
            )
        except AssetError as exc:
            return process_error_response(exc)

        data = UploadStatusResponseSerializer(asset).data
        return Response(data, status=status.HTTP_200_OK)


class AssetUploadCommitView(APIView):
    permission_classes = (IsAuthenticated,)
    upload_api = None

    def _get_upload_api(self):
        return self.upload_api or build_upload_api()

    @extend_schema(
        summary='Синхронно подтвердить загрузку',
        description='Вызывается фронтом после успешной загрузки файла в S3.',
        tags=['Assets'],
        request=None,
        responses={
            200: UploadStatusResponseSerializer,
            400: AssetErrorResponseSerializer,
            401: AssetErrorResponseSerializer,
            403: AssetErrorResponseSerializer,
            404: AssetErrorResponseSerializer,
            409: AssetErrorResponseSerializer,
            503: AssetErrorResponseSerializer,
        },
    )
    def post(self, request, asset_id):
        try:
            asset = self._get_upload_api().commit_for_user(
                user=request.user,
                asset_id=asset_id,
            )
        except AssetError as exc:
            return process_error_response(exc)

        data = UploadStatusResponseSerializer(asset).data
        return Response(data, status=status.HTTP_200_OK)
