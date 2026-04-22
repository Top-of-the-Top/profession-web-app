from rest_framework import status
from rest_framework.response import Response

from ..services.errors import (
    AssetAlreadyCommitted,
    AssetBindConflict,
    AssetCommitMismatch,
    AssetIntentNotAllowed,
    AssetNotFound,
    AssetPermissionDenied,
    AssetPolicyViolation,
    AssetStatusInvalid,
    AssetStorageUnavailable,
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


def asset_error_response(exc, http_status=None):
    payload = {
        'status': 'error',
        'code': exc.code,
        'message': exc.message,
        'details': exc.details or {},
    }
    if http_status is None:
        http_status = ASSET_ERROR_STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return Response(payload, status=http_status)
