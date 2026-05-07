import logging

from django.conf import settings
from django.core.mail import send_mail
from sms import send_sms

logger = logging.getLogger(__name__)


def send_verification_email(email, code):
    try:
        send_mail(
            subject="Подтверждение email",
            message=f"Ваш код подтверждения: {code}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True, "Письмо отправлено"

    except Exception as e:
        logger.exception("Не удалось отправить письмо с кодом подтверждения на %s", email)
        return False, f"Ошибка отправки: {str(e)}"


def send_verification_sms(phone_number, code):
    try:
        send_sms(
            body=f"Ваш код подтверждения Профессия: {code}",
            originator=settings.DEFAULT_FROM_SMS,
            recipients=[phone_number],
            fail_silently=False,
        )
        return True, "СМС отправлено"

    except Exception as e:
        logger.exception("Не удалось отправить СМС с кодом подтверждения на %s", phone_number)
        return False, f"Ошибка отправки СМС: {str(e)}"


def send_reset_password_email(email, recover_url):
    try:
        send_mail(
            subject="Сброс пароля",
            message=f"Перейдите по ссылке для сброса пароля: {recover_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True, "Письмо отправлено"

    except Exception as e:
        logger.exception("Не удалось отправить письмо для сброса пароля на %s", email)
        return False, f"Ошибка отправки: {str(e)}"


def send_reset_password_sms(phone_number, reset_code):
    try:
        send_sms(
            body=f"Код для сброса пароля Профессия: {reset_code}",
            originator=settings.DEFAULT_FROM_SMS,
            recipients=[phone_number],
            fail_silently=False,
        )
        return True, "СМС отправлено"

    except Exception as e:
        logger.exception("Не удалось отправить СМС для сброса пароля на %s", phone_number)
        return False, f"Ошибка отправки СМС: {str(e)}"
