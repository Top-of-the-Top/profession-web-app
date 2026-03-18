from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..tasks import create_and_send_notification
from ..models import Notification
import pika
import json
import time
import logging
from django.http import StreamingHttpResponse

logger = logging.getLogger(__name__)

import json
import time
import asyncio  # Добавьте это
from django.http import StreamingHttpResponse
from asgiref.sync import sync_to_async  # Добавьте это


def sse_notifications(request):
    async def event_stream():  # Сделаем генератор асинхронным
        # Получаем последний ID один раз при подключении
        def get_last_id():
            return Notification.objects.latest('id').id if Notification.objects.exists() else 0

        last_id = await sync_to_async(get_last_id)()

        while True:
            # Отправляем heartbeat сразу
            yield b": heartbeat\n\n"

            # Обертываем работу с БД в sync_to_async
            def get_new_notifications(l_id):
                return list(Notification.objects.filter(id__gt=l_id).order_by('id'))

            recent = await sync_to_async(get_new_notifications)(last_id)

            for notification in recent:
                data = {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "created_at": notification.created_at.isoformat()
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode('utf-8')
                last_id = notification.id

            await asyncio.sleep(1)  # Используем асинхронный сон!

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Важно для Nginx/Daphne
    return response


@api_view(['POST'])
def trigger_notification(request):
    user_id = request.data['user_id']
    title = request.data['title']
    message = request.data['message']

    task = create_and_send_notification.delay(user_id, title, message)
    return Response({
        'status': 'sent',
        'task_id': task.id
    }, status=202)
