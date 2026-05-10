from rest_framework import status


class VerificationError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.details = {}
        self.status = status.HTTP_400_BAD_REQUEST
        super().__init__(message)


class UserError(Exception):
    code = "USER_ERROR"
    message = "Ошибка операции с пользователем."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class ContactRequired(UserError):
    code = "CONTACT_REQUIRED"
    message = "Укажите email или номер телефона."
    status = status.HTTP_400_BAD_REQUEST


class RateLimitExceeded(UserError):
    code = "RATE_LIMIT_EXCEEDED"
    message = "Слишком много запросов."
    status = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, retry_after=None):
        details = {"retry_after": retry_after} if retry_after is not None else {}
        super().__init__(details=details)
        if retry_after is not None:
            self.message = f"Слишком много запросов. Повторите через {retry_after} сек."


class ValidationFailed(UserError):
    code = "VALIDATION_ERROR"
    message = "Ошибка валидации данных."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, errors):
        super().__init__(details=errors if isinstance(errors, dict) else {"errors": errors})


class UserNotFound(UserError):
    code = "USER_NOT_FOUND"
    message = "Пользователь не найден."
    status = status.HTTP_403_FORBIDDEN


class EmailAlreadyExists(UserError):
    code = "EMAIL_ALREADY_EXISTS"
    message = "Этот email уже используется."
    status = status.HTTP_400_BAD_REQUEST


class PhoneAlreadyExists(UserError):
    code = "PHONE_ALREADY_EXISTS"
    message = "Этот номер телефона уже используется."
    status = status.HTTP_400_BAD_REQUEST


class RefreshTokenInvalid(UserError):
    code = "REFRESH_TOKEN_INVALID"
    message = "Невалидный или истёкший refresh_token."
    status = status.HTTP_401_UNAUTHORIZED


class RefreshTokenMissing(UserError):
    code = "REFRESH_TOKEN_MISSING"
    message = "refresh_token обязателен."
    status = status.HTTP_401_UNAUTHORIZED


class ResetTokenInvalid(UserError):
    code = "RESET_TOKEN_INVALID"
    message = "Невалидный или истёкший токен сброса пароля."
    status = status.HTTP_403_FORBIDDEN


class ResetTokenMissing(UserError):
    code = "RESET_TOKEN_MISSING"
    message = "Поля token и password обязательны."
    status = status.HTTP_403_FORBIDDEN


class EmailSendFailed(UserError):
    code = "EMAIL_SEND_FAILED"
    message = "Не удалось отправить письмо."
    status = status.HTTP_500_INTERNAL_SERVER_ERROR


class SmsSendFailed(UserError):
    code = "SMS_SEND_FAILED"
    message = "Не удалось отправить SMS."
    status = status.HTTP_500_INTERNAL_SERVER_ERROR


class AvatarBindFailed(UserError):
    code = "AVATAR_BIND_NOT_APPLIED"
    message = "Не удалось привязать новый аватар к профилю."
    status = status.HTTP_409_CONFLICT


class OAuthInvalidRequest(UserError):
    code = "OAUTH_INVALID_REQUEST"
    message = "Отсутствуют обязательные параметры OAuth-запроса."
    status = status.HTTP_400_BAD_REQUEST


class OAuthInvalidState(UserError):
    code = "OAUTH_INVALID_STATE"
    message = "OAuth state недействителен или истёк."
    status = status.HTTP_400_BAD_REQUEST


class OAuthInvalidCode(UserError):
    code = "OAUTH_INVALID_CODE"
    message = "Не удалось обменять код на токены OAuth-провайдера."
    status = status.HTTP_400_BAD_REQUEST


class OAuthMissingProfileData(UserError):
    code = "OAUTH_MISSING_PROFILE_DATA"
    message = "OAuth-провайдер не вернул email или номер телефона."
    status = status.HTTP_400_BAD_REQUEST


class OAuthProviderUnavailable(UserError):
    code = "OAUTH_PROVIDER_UNAVAILABLE"
    message = "OAuth-провайдер временно недоступен."
    status = status.HTTP_502_BAD_GATEWAY
