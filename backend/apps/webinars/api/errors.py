from rest_framework import status


class WebinarError(Exception):
    code = "WEBINAR_ERROR"
    message = "Ошибка операции с вебинаром."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class WebinarAlreadyLive(WebinarError):
    code = "WEBINAR_ALREADY_LIVE"
    message = "Вебинар уже запущен."
    status = status.HTTP_409_CONFLICT


class WebinarNotLive(WebinarError):
    code = "WEBINAR_NOT_LIVE"
    message = "Вебинар не запущен."
    status = status.HTTP_404_NOT_FOUND


class WebinarScheduleConflict(WebinarError):
    code = "WEBINAR_SCHEDULE_CONFLICT"
    message = "Нельзя изменить расписание вебинара, который сейчас идёт."
    status = status.HTTP_409_CONFLICT


class WhiteboardCreateFailed(WebinarError):
    code = "WHITEBOARD_CREATE_FAILED"
    message = "Не удалось создать комнату доски."
    status = status.HTTP_502_BAD_GATEWAY


class RecordingAlreadyActive(WebinarError):
    code = "RECORDING_ALREADY_ACTIVE"
    message = "Запись уже идёт."
    status = status.HTTP_409_CONFLICT


class RecordingNotActive(WebinarError):
    code = "RECORDING_NOT_ACTIVE"
    message = "Активная запись не найдена."
    status = status.HTTP_400_BAD_REQUEST


class RecordingScreenshotsMissing(WebinarError):
    code = "RECORDING_SCREENSHOTS_MISSING"
    message = "Скриншоты не переданы."
    status = status.HTTP_400_BAD_REQUEST


class RecorderTokenInvalid(WebinarError):
    code = "RECORDER_TOKEN_INVALID"
    message = "Токен рекордера недействителен или истёк."
    status = status.HTTP_403_FORBIDDEN


class RecorderTokenMissing(WebinarError):
    code = "RECORDER_TOKEN_MISSING"
    message = "Токен рекордера обязателен."
    status = status.HTTP_400_BAD_REQUEST


class WebinarNotFound(WebinarError):
    code = "WEBINAR_NOT_FOUND"
    message = "Вебинар не найден."
    status = status.HTTP_404_NOT_FOUND


class RecordingNotFound(WebinarError):
    code = "RECORDING_NOT_FOUND"
    message = "Запись не найдена."
    status = status.HTTP_404_NOT_FOUND


class ScreenshotsConversionFailed(WebinarError):
    code = "SCREENSHOTS_CONVERSION_FAILED"
    message = "Не удалось обработать скриншоты."
    status = status.HTTP_500_INTERNAL_SERVER_ERROR
