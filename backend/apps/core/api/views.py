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

class BaseAssetView(APIView):
    permission_classes = (IsAuthenticated,)
    
    @property
    def upload_api(self):
        return build_upload_api()


class AssetUploadInitiateView(BaseAssetView):
    @extend_schema(
        summary='Инициировать загрузку файла',
        description='Создает запись об ассете (PENDING) и выдает presigned URL для S3.',
        tags=['Assets'],
        request=InitiateUploadRequestSerializer,
        responses={
            201: InitiateUploadResponseSerializer,
            400: AssetErrorResponseSerializer,
            403: AssetErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = InitiateUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Возвращает Asset + upload_url
            result = self.upload_api.initiate_upload(
                user=request.user,
                **serializer.validated_data
            )
            return Response(
                InitiateUploadResponseSerializer(result).data, 
                status=status.HTTP_201_CREATED
            )
        except AssetError as exc:
            return process_error_response(exc)


class AssetUploadStatusView(BaseAssetView):
    @extend_schema(
        summary='Статус загрузки ассета',
        description='Проверка состояния ассета (PENDING/READY/ERROR).',
        tags=['Assets'],
        responses={
            200: UploadStatusResponseSerializer,
            403: AssetErrorResponseSerializer,
            404: AssetErrorResponseSerializer,
        },
    )
    def get(self, request, asset_id):
        try:
            # Здесь происходит проверка прав внутри фасада
            asset = self.upload_api.get_upload_status(
                user=request.user,
                asset_id=asset_id,
            )
            return Response(
                UploadStatusResponseSerializer(asset).data, 
                status=status.HTTP_200_OK
            )
        except AssetError as exc:
            return process_error_response(exc)