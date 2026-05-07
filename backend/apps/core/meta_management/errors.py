from rest_framework import status


class AssetError(Exception):
    code = "ASSET_ERROR"
    message = "Ошибка обработки медиа-ассета."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class AssetNotFound(AssetError):
    code = "ASSET_NOT_FOUND"
    message = "Ассет не найден."
    status = status.HTTP_404_NOT_FOUND


class AssetIntentNotAllowed(AssetError):
    code = "ASSET_INTENT_NOT_ALLOWED"
    message = "Указанное назначение загрузки недопустимо."
    status = status.HTTP_400_BAD_REQUEST


class AssetPolicyViolation(AssetError):
    code = "ASSET_POLICY_VIOLATION"
    message = "Файл не соответствует политике загрузки."
    status = status.HTTP_400_BAD_REQUEST


class AssetCommitMismatch(AssetError):
    code = "ASSET_COMMIT_MISMATCH"
    message = "Параметры загруженного файла не совпадают с заявленными."
    status = status.HTTP_400_BAD_REQUEST


class AssetAlreadyCommitted(AssetError):
    code = "ASSET_ALREADY_COMMITTED"
    message = "Ассет уже подтверждён."
    status = status.HTTP_409_CONFLICT


class AssetStatusInvalid(AssetError):
    code = "ASSET_STATUS_INVALID"
    message = "Операция недопустима для текущего статуса ассета."
    status = status.HTTP_409_CONFLICT


class AssetPermissionDenied(AssetError):
    code = "ASSET_PERMISSION_DENIED"
    message = "Недостаточно прав на операцию с ассетом."
    status = status.HTTP_403_FORBIDDEN


class AssetStorageUnavailable(AssetError):
    code = "ASSET_STORAGE_UNAVAILABLE"
    message = "Хранилище временно недоступно."
    status = status.HTTP_503_SERVICE_UNAVAILABLE


class AssetBindConflict(AssetError):
    code = "ASSET_BIND_CONFLICT"
    message = "Такая привязка уже существует."
    status = status.HTTP_409_CONFLICT
