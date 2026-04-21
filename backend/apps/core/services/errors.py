class AssetError(Exception):
    code = 'ASSET_ERROR'
    message = 'Ошибка обработки медиа-ассета.'

    def __init__(self, message=None, *, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}


class AssetNotFound(AssetError):
    code = 'ASSET_NOT_FOUND'
    message = 'Ассет не найден.'


class AssetIntentNotAllowed(AssetError):
    code = 'ASSET_INTENT_NOT_ALLOWED'
    message = 'Указанное назначение загрузки недопустимо.'


class AssetPolicyViolation(AssetError):
    code = 'ASSET_POLICY_VIOLATION'
    message = 'Файл не соответствует политике загрузки.'


class AssetCommitMismatch(AssetError):
    code = 'ASSET_COMMIT_MISMATCH'
    message = 'Параметры загруженного файла не совпадают с заявленными.'


class AssetAlreadyCommitted(AssetError):
    code = 'ASSET_ALREADY_COMMITTED'
    message = 'Ассет уже подтверждён.'


class AssetStatusInvalid(AssetError):
    code = 'ASSET_STATUS_INVALID'
    message = 'Операция недопустима для текущего статуса ассета.'


class AssetPermissionDenied(AssetError):
    code = 'ASSET_PERMISSION_DENIED'
    message = 'Недостаточно прав на операцию с ассетом.'


class AssetStorageUnavailable(AssetError):
    code = 'ASSET_STORAGE_UNAVAILABLE'
    message = 'Хранилище временно недоступно.'


class AssetBindConflict(AssetError):
    code = 'ASSET_BIND_CONFLICT'
    message = 'Такая привязка уже существует.'
