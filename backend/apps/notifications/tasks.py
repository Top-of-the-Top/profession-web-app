from celery import shared_task
from django.utils import timezone
from .rabbit import publish_event # Импортируем твою обновленную функцию

@shared_task
def send_course_notification(course_id, title, message):
    """Рассылка на весь курс через RabbitMQ Topic"""
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
    payload = {
        "type": "personal",
        "title": title,
        "message": message,
        "created_at": timezone.now().isoformat()
    }
    # Используем ключ 'user.ID'
    publish_event(routing_key=f"user.{user_id}", payload=payload)