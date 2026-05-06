from rest_framework import status

class HomeworkServiceError(Exception):
    code = 'HOMEWORK_ERROR'
    message = 'Ошибка обработки домашнего задания.'
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class AttemptAlreadySubmitted(HomeworkServiceError):
    code = 'ATTEMPT_ALREADY_SUBMITTED'
    message = 'Попытка уже отправлена на проверку.'
    status = status.HTTP_409_CONFLICT


class AttemptItemNotFound(HomeworkServiceError):
    code = 'ATTEMPT_ITEM_NOT_FOUND'
    message = 'Элемент не принадлежит текущей попытке.'
    status = status.HTTP_400_BAD_REQUEST


class AttemptPayloadMismatch(HomeworkServiceError):
    code = 'ATTEMPT_PAYLOAD_MISMATCH'
    message = 'Переданный attempt_id не совпадает с текущей попыткой.'
    status = status.HTTP_400_BAD_REQUEST


class AttemptValidationError(HomeworkServiceError):
    code = 'VALIDATION_ERROR'
    message = 'Ошибка в данных запроса.'
    status = status.HTTP_400_BAD_REQUEST


class UploadFileTooLarge(HomeworkServiceError):
    code = 'FILE_TOO_LARGE'
    message = 'Файл больше 10 МБ.'
    status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


class StorageUnavailable(HomeworkServiceError):
    code = 'STORAGE_ERROR'
    message = 'Не удалось связаться с облачным хранилищем.'
    status = status.HTTP_503_SERVICE_UNAVAILABLE


class AttemptNotSubmitted(HomeworkServiceError):
    code = 'ATTEMPT_NOT_SUBMITTED'
    message = 'Попытка ещё не отправлена на проверку.'
    status = status.HTTP_409_CONFLICT


class ReviewItemNotFound(HomeworkServiceError):
    code = 'REVIEW_ITEM_NOT_FOUND'
    message = 'Ответ на задание не найден в данной попытке.'
    status = status.HTTP_400_BAD_REQUEST


class ReviewPointsExceeded(HomeworkServiceError):
    code = 'REVIEW_POINTS_EXCEEDED'
    message = 'Выставленные баллы превышают максимум за задание.'
    status = status.HTTP_400_BAD_REQUEST


class RequestValidationError(HomeworkServiceError):
    code = 'VALIDATION_ERROR'
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail):
        super().__init__(message=self._extract(detail))

    @staticmethod
    def _extract(detail):
        if isinstance(detail, list):
            return RequestValidationError._extract(detail[0]) if detail else 'Неверный запрос.'
        if isinstance(detail, dict):
            first = next(iter(detail.values()), None)
            return RequestValidationError._extract(first) if first is not None else 'Неверный запрос.'
        return str(detail)


class InternalError(HomeworkServiceError):
    code = 'INTERNAL_ERROR'
    message = 'Внутренняя ошибка сервера.'
    status = status.HTTP_500_INTERNAL_SERVER_ERROR