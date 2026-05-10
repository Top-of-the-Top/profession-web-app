from rest_framework import status


class StatsError(Exception):
    code = "STATS_ERROR"
    message = "Ошибка получения статистики."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class StatsAccessDenied(StatsError):
    code = "STATS_ACCESS_DENIED"
    message = "Доступ к статистике разрешён только преподавателям и модераторам."
    status = status.HTTP_403_FORBIDDEN


class StudentCardAccessDenied(StatsError):
    code = "STUDENT_CARD_ACCESS_DENIED"
    message = "Нет доступа к карточке этого ученика."
    status = status.HTTP_403_FORBIDDEN
