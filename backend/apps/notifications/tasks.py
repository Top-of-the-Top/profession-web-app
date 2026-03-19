from celery import shared_task
from django.utils import timezone
from .rabbit import publish_event
from .models import  Notification
@shared_task
def send_course_notification(course_id, title, message):
    """Рассылка на весь курс через RabbitMQ Topic"""
    Notification.objects.create(
        course_id=course_id,
        title=title,
        message=message,
        is_system=True
    )

    payload = {
        "type": "course_update",
        "course_id": course_id,
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }
    # Используем ключ 'course.ID', на который подписаны все студенты этого курса
    publish_event(routing_key=f"course.{course_id}", payload=payload)

@shared_task
def send_personal_notification(user_id, title, message):
    """Личное уведомление конкретному пользователю"""

    Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        is_system=False
    )

    payload = {
        "type": "personal",
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }
    # Используем ключ 'user.ID'
    publish_event(routing_key=f"user.{user_id}", payload=payload)