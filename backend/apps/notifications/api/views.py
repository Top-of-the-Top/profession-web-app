import json
import asyncio
import aio_pika
import logging

from django.http import StreamingHttpResponse, HttpResponse, HttpResponseNotAllowed
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer
from ..models import Notification

from apps.courses.models import PurchasedCourse

logger = logging.getLogger(__name__)
User = get_user_model()

@api_view(['GET']) # Решил проще данную штуку точечно сделать функцией. Введение cbv для этого избыточно
@permission_classes([IsAuthenticated])

def get_notifications_for_user(request):
    user = request.user

    purchased_course_ids = user.get_purchased_courses_ids()

    notifications = Notification.objects.filter(
        Q(user=user) | Q(course_id__in=purchased_course_ids) | Q(notification_type=Notification.SYSTEM)
    ).distinct()

    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@permission_classes([IsAuthenticated])
async def sse_notifications(request):
    # async - функция корутина, которая умеет приостанавливать свое выполнение ( замораживаться в ожидании )
    # Под капотом async - создает state machine, которая умеет сохранять локальные переменные и контекст и соответственно состояние

    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    user = request.user

    async def event_stream():
        # В этой точке await сигнализирует что операция занимает какое-то время
        # В этой точке мы идем заниматься своими вещами, когда мы получаем отсюда сообщение что "готово", то продолжаем с этого места
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()

        exchange = await channel.declare_exchange('notifications', aio_pika.ExchangeType.TOPIC)

        queue = await channel.declare_queue(exclusive=True)

        await queue.bind(exchange, routing_key=f"user.{user.pk}")

        user_course_ids = await user.aget_purchased_course_ids()

        for c_id in user_course_ids:
            await queue.bind(exchange, routing_key=f"course.{c_id}")

        await queue.bind(exchange, routing_key="system.all")

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
