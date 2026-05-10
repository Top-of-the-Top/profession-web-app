from rest_framework import status


class AdminPanelError(Exception):
    code = "ADMIN_PANEL_ERROR"
    message = "Ошибка операции в панели администратора."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class UserNotTeacher(AdminPanelError):
    code = "USER_NOT_TEACHER"
    message = "Пользователь не является преподавателем."
    status = status.HTTP_400_BAD_REQUEST


class AuthorAlreadyOnCourse(AdminPanelError):
    code = "AUTHOR_ALREADY_ON_COURSE"
    message = "Пользователь уже является автором этого курса."
    status = status.HTTP_400_BAD_REQUEST


class AuthorNotOnCourse(AdminPanelError):
    code = "AUTHOR_NOT_ON_COURSE"
    message = "Пользователь не является автором этого курса."
    status = status.HTTP_400_BAD_REQUEST


class CourseAlreadyPublished(AdminPanelError):
    code = "COURSE_ALREADY_PUBLISHED"
    message = "Курс уже опубликован."
    status = status.HTTP_400_BAD_REQUEST


class CourseAlreadyDraft(AdminPanelError):
    code = "COURSE_ALREADY_DRAFT"
    message = "Курс уже находится в статусе черновика."
    status = status.HTTP_400_BAD_REQUEST


class InvitationNotFound(AdminPanelError):
    code = "INVITATION_NOT_FOUND"
    message = "Приглашение не найдено."
    status = status.HTTP_404_NOT_FOUND


class InvitationAlreadyUsed(AdminPanelError):
    code = "INVITATION_ALREADY_USED"
    message = "Приглашение уже использовано."
    status = status.HTTP_400_BAD_REQUEST


class InvitationExpired(AdminPanelError):
    code = "INVITATION_EXPIRED"
    message = "Срок действия ссылки истёк."
    status = status.HTTP_400_BAD_REQUEST


class InvitationSendFailed(AdminPanelError):
    code = "INVITATION_SEND_FAILED"
    message = "Не удалось отправить письмо с приглашением."
    status = status.HTTP_500_INTERNAL_SERVER_ERROR
