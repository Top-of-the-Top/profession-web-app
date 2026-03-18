from celery import shared_task
from .models import Notification
from django.utils import timezone

from .rabbit  import publish_broadcast_event


@shared_task(bind=True, max_retries=3)
def create_and_send_notification(self, user_id, title, message):
    """БД + RabbitMQ fanout exchange (одна очередь для всех через SSE)"""

    # 1. Создаем уведомление в БД
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
        return f"✅ Notification {notification.id} sent via RabbitMQ fanout"

    except Exception as exc:
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)

