from rest_framework.decorators import api_view
from rest_framework.response import Response
from ..tasks import create_and_send_notification
from ..models import Notification
import pika
import logging
import json
import asyncio
from django.http import StreamingHttpResponse
from asgiref.sync import sync_to_async


logger = logging.getLogger(__name__)

def sse_notifications(request):
    """Функция для просмотра текущих уведомлений"""
    async def event_stream():
        # Получаем последний ID один раз при подключении
        def get_last_id():
            return Notification.objects.latest('id').id if Notification.objects.exists() else 0

        last_id = await sync_to_async(get_last_id)()

        while True:
            yield b": heartbeat\n\n" # Проверка соединения + чтобы не закрывалось автоматически соединение

            def get_new_notifications(l_id): # функция для получения всех уведомлений после последнего полученного
                return list(Notification.objects.filter(id__gt=l_id).order_by('id'))

            recent = await sync_to_async(get_new_notifications)(last_id) # Оборачиваем код и превращаем данный запрос в асинхронный, чтобы избежать долгого ожидания

            for notification in recent:
                data = {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "created_at": notification.created_at.isoformat()
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode('utf-8')
                last_id = notification.id

            await asyncio.sleep(5)  # Проверяем уведомления раз в 5 секунд

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream') # Это спецаильный вид ответа - потока
    response['Cache-Control'] = 'no-cache' # Убираем кеширование полученных уведомлений
    response['X-Accel-Buffering'] = 'no'  # Короче это штука, которая отключает накапливание буффера перед отправкой. Все отправляется мгновенно
    return response


@api_view(['POST'])
def trigger_notification(request):
    """Это функция - триггер, для ручной отправки сообщений в очередь"""
    user_id = request.data['user_id']
    title = request.data['title']
    message = request.data['message']

    task = create_and_send_notification.delay(user_id, title, message)
    return Response({
        'status': 'sent',
        'task_id': task.id
    }, status=202)
