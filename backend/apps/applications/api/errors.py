from rest_framework import status


class ApplicationError(Exception):
    code = "APPLICATION_ERROR"
    message = "Ошибка операции с заявкой."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class ApplicationNotSpecialCourse(ApplicationError):
    code = "APPLICATION_NOT_SPECIAL_COURSE"
    message = "На этот курс нельзя подать заявку — он не является специальным."
    status = status.HTTP_400_BAD_REQUEST


class ApplicationAlreadyEnrolled(ApplicationError):
    code = "APPLICATION_ALREADY_ENROLLED"
    message = "Вы уже записаны на этот курс."
    status = status.HTTP_400_BAD_REQUEST


class ApplicationAlreadySubmitted(ApplicationError):
    code = "APPLICATION_ALREADY_SUBMITTED"
    message = "Заявка на этот курс уже подана."
    status = status.HTTP_409_CONFLICT


class ApplicationNotFound(ApplicationError):
    code = "APPLICATION_NOT_FOUND"
    message = "Заявка не найдена."
    status = status.HTTP_404_NOT_FOUND


class ApplicationAlreadyReviewed(ApplicationError):
    code = "APPLICATION_ALREADY_REVIEWED"
    message = "Заявка уже рассмотрена и не может быть изменена."
    status = status.HTTP_409_CONFLICT


class ApplicationWithdrawForbidden(ApplicationError):
    code = "APPLICATION_WITHDRAW_FORBIDDEN"
    message = "Нельзя отозвать уже рассмотренную заявку."
    status = status.HTTP_409_CONFLICT


class ApplicationSelfServiceForbiddenForStaff(ApplicationError):
    code = "APPLICATION_SELF_SERVICE_FORBIDDEN_FOR_STAFF"
    message = (
        "Подача и отзыв заявки на специальный курс доступны только пользователям с ролью «студент»."
    )
    status = status.HTTP_403_FORBIDDEN
