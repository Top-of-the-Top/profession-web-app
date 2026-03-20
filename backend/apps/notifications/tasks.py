from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .rabbit import publish_event
from .models import Notification

User = get_user_model()

@shared_task
def send_course_notification(course_id, title, message, html_body=None, send_email=False):
    """Рассылка на весь курс: запись в БД + RabbitMQ + (опционально) Почта"""

    notif = Notification.objects.create(
        course_id=course_id,
        title=title,
        message=message,
        html_message=html_body,
        is_system=True
    )

    payload = {
        "id": notif.id,
        "type": "course_update",
        "course_id": course_id,
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }

    publish_event(routing_key=f"course.{course_id}", payload=payload)

    if send_email and html_body:
        send_mass_course_email.delay(course_id, title, html_body)


@shared_task
def send_personal_notification(user_id, title, message, html_body=None, send_email=True):
    """Личное уведомление: запись в БД + RabbitMQ + Почта"""

    notif = Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        html_message=html_body,
        is_system=False
    )

    payload = {
        "id": notif.id,
        "type": "personal",
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }

    publish_event(routing_key=f"user.{user_id}", payload=payload)

    if send_email and html_body:
        send_single_email.delay(user_id, title, html_body)


@shared_task
def send_single_email(user_id, subject, html_content):
    """Отдельная задача для отправки письма, чтобы не блокировать основной поток"""
    try:
        user = User.objects.get(pk=user_id)
        if user.email:
            pass
    except User.DoesNotExist:
        pass