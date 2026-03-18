from celery import shared_task
from .models import Notification
from django.utils import timezone
from .rabbit  import publish_broadcast_event


@shared_task(bind=True, max_retries=3) # Этот код живет не в основном потоке, а в потоке celery worker, поэтому здесь синхронно выполняе задачи
def create_and_send_notification(self, user_id, title, message):
    """Создание и отправка уведомления для конкретного пользователя в единую очередь"""

    notification = Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message
    )

    try:
        payload = {
            "type": "notification",
            'id': notification.id,
            'user_id': user_id,
            'title': title,
            'message': message,
            'created_at': timezone.now().isoformat()
        }
        publish_broadcast_event(payload=payload)
        return f"Notification {notification.id} sent via RabbitMQ fanout"

    except Exception as exc:
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc) # с каждым разом время ожидания увеличивается по экспоненте

