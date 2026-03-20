import json
import asyncio
import aio_pika
import logging

from django.http import StreamingHttpResponse, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model

# Инструменты для работы асинхронного кода с синхронной ORM Django
from asgiref.sync import sync_to_async

# Декораторы для API (DRF)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# Импорты твоих моделей
# (Пути могут немного отличаться в зависимости от твоей структуры)
from apps.courses.models import PurchasedCourse
from ..rabbit import NOTIFICATIONS_EXCHANGE, NOTIFICATIONS_EXCHANGE_TYPE

logger = logging.getLogger(__name__)
User = get_user_model()

@api_view(['GET']) # Решил проще данную штуку точечно сделать функцией. Введение cbv для этого избыточно
@permission_classes([IsAuthenticated])
def get_notifications_for_user(request):
    """Посмотреть уведомления для текущего пользователя из request"""

    user = request.user
    user_notifications = Notification.objects.filter(user=user)


    serializer = NotificationSerializer(user_notifications, many=True)

    return HttpResponse(serializer.data)

async def get_user_courses(user):
    cache_key = f"user_courses_{user.id}"
    courses = await cache.aget(cache_key) # Асинхронный кэш
    if courses is None:
        qs = PurchasedCourse.objects.filter(user=user).values_list('course_id', flat=True)
        courses = await sync_to_async(list)(qs)
        await cache.aset(cache_key, courses, timeout=3600)
    return courses

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def sse_notifications(request):
    # async - функция корутина, которая умеет приостанавливать свое выполнение ( замораживаться в ожидании )
    # Под капотом async - создает state machine, которая умеет сохранять локальные переменные и контекст и соответственно состояние
    async def event_stream():
        # В этой точке await сигнализирует что операция занимает какое-то время
        # В этой точке мы идем заниматься своими вещами, когда мы получаем отсюда сообщение что "готово", то продолжаем с этого места
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()

        exchange = await channel.declare_exchange('notifications', aio_pika.ExchangeType.TOPIC)

        queue = await channel.declare_queue(exclusive=True)

        await queue.bind(exchange, routing_key=f"user.{request.user.id}")

        user_course_ids = await get_user_courses(request.user)
        for c_id in user_course_ids:
            await queue.bind(exchange, routing_key=f"course.{c_id}")

        try:
            async with queue.iterator() as queue_iter:
                yield b": heartbeat\n\n"

                async for message in queue_iter:
                    async with message.process():
                        # Как только в RabbitMQ пришло сообщение — оно тут же летит в SSE
                        data = json.loads(message.body.decode())
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode('utf-8')
        finally:
            # При закрытии вкладки браузером — очередь в RabbitMQ удалится сама
            await connection.close()

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
