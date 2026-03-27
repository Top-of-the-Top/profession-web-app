from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from .rabbit import publish_event
from .models import Notification
from apps.users.api.utils import decrypt_data
from apps.users.models import User
from django.conf import settings

import logging

# Создаем экземпляр логгера для текущего модуля
logger = logging.getLogger(__name__)

@shared_task
def send_course_notification(course_id, title, message):
    """Рассылка на весь курс: запись в БД + RabbitMQ + (опционально) Почта"""

    notif = Notification.objects.create(
        course_id=course_id,
        title=title,
        notification_type=Notification.COURSE,
        message=message,
    )

    payload = {
        "id": notif.id,
        "type": "course_update",
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }

    publish_event(routing_key=f"course.{course_id}", payload=payload)

@shared_task
def send_personal_notification(user_id, title, message):
    """Личное уведомление: запись в БД + RabbitMQ + Почта"""

    notif = Notification.objects.create(
        user_id=user_id,
        title=title,
        notification_type=Notification.PERSONAL,
        message=message,
    )

    payload = {
        "id": notif.id,
        "type": "personal",
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }

    publish_event(routing_key=f"user.{user_id}", payload=payload)

@shared_task
def send_system_notification(title, message):
    """Общесистемные уведомления: запись в БД + RabbitMQ + Почта"""

    notif = Notification.objects.create(
        title=title,
        notification_type=Notification.SYSTEM,
        message=message,
    )

    payload = {
        "id": notif.id,
        "type": "system",
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }

    publish_event(routing_key="system.all", payload=payload)


@shared_task
def send_single_email(user_id, subject, message):
    """Отдельная задача для отправки письма, чтобы не блокировать основной поток"""
    try:
        user = User.objects.get(pk=user_id)
        user_email = decrypt_data(user.email_cipher)
        if user_email:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
            )
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
    except Exception as e:
        logger.error(f"Error sending email to user {user_id}: {e}")


@shared_task
def send_mass_course_email(course_id, subject, message):
    """Отдельная жирная задача для отправки писем всем, кто зарегистрирован на курс"""
    users = User.objects.filter(
        purchased_courses__course_id=course_id
    ).distinct()

    for user in users:
        send_single_email(user.id, subject, message)


@shared_task
def send_mass_system_email(subject, message):
    """Отдельная жирная задача для отправки все пользователям системы"""

    for user in User.objects.all():
        send_single_email(user.id, subject, message)
