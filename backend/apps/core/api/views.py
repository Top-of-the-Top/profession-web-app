from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.errors import (
    AssetAlreadyCommitted,
    AssetBindConflict,
    AssetCommitMismatch,
    AssetError,
    AssetIntentNotAllowed,
    AssetNotFound,
    AssetPermissionDenied,
    AssetPolicyViolation,
    AssetStatusInvalid,
    AssetStorageUnavailable,
)
from ..services.factory import build_upload_api
from .serializers import (
    AssetErrorResponseSerializer,
    InitiateUploadRequestSerializer,
    InitiateUploadResponseSerializer,
    UploadStatusResponseSerializer,
)


ASSET_ERROR_STATUS_MAP = {
    AssetNotFound: status.HTTP_404_NOT_FOUND,
    AssetIntentNotAllowed: status.HTTP_400_BAD_REQUEST,
    AssetPolicyViolation: status.HTTP_400_BAD_REQUEST,
    AssetCommitMismatch: status.HTTP_400_BAD_REQUEST,
    AssetAlreadyCommitted: status.HTTP_409_CONFLICT,
    AssetStatusInvalid: status.HTTP_409_CONFLICT,
    AssetBindConflict: status.HTTP_409_CONFLICT,
    AssetPermissionDenied: status.HTTP_403_FORBIDDEN,
    AssetStorageUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _error_response(exc, http_status=None):
    payload = {
        'status': 'error',
        'code': exc.code,
        'message': exc.message,
        'details': exc.details or {},
    }
    if http_status is None:
        http_status = ASSET_ERROR_STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return Response(payload, status=http_status)


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
            return _error_response(exc)

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
            return _error_response(exc)

        data = UploadStatusResponseSerializer(asset).data
        return Response(data, status=status.HTTP_200_OK)
