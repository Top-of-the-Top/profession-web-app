import json
import asyncio
import aio_pika
import logging

from django.http import StreamingHttpResponse, HttpResponse, HttpResponseNotAllowed
from rest_framework.response import Response
from django.conf import settings
from asgiref.sync import sync_to_async
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .serializers import NotificationSerializer
from ..models import Notification
from apps.users.models import User
from apps.courses.models import PurchasedCourse

logger = logging.getLogger(__name__)



@extend_schema(
    tags=['Notifications'],
    summary='Список уведомлений пользователя',
    responses={200: NotificationSerializer(many=True)},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications_for_user(request):
    user = request.user

    purchased_course_ids = user.get_purchased_courses_ids()

    notifications = Notification.objects.filter(
        Q(user=user) | Q(course_id__in=purchased_course_ids) | Q(notification_type=Notification.SYSTEM)
    ).distinct()

    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@extend_schema(
    tags=['Notifications'],
    summary='Поток уведомлений (SSE)',
    description='Server-Sent Events; требуется query-параметр token (JWT access).',
    parameters=[
        OpenApiParameter(
            name='token',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description='JWT access token',
        ),
    ],
    responses={
        200: {
            'description': 'Поток text/event-stream',
            'content': {'text/event-stream': {}},
        },
        401: {'description': 'Нет или неверный token'},
    },
)
async def sse_notifications(request):
    # async - функция корутина, которая умеет приостанавливать свое выполнение ( замораживаться в ожидании )
    # Под капотом async - создает state machine, которая умеет сохранять локальные переменные и контекст и соответственно состояние

    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    token = request.GET.get('token')
    if not token:
        return HttpResponse("Missing token", status=401)

    try:
        access_token = AccessToken(token)
        user_id = access_token.get('user_id')
        if not user_id:
            return HttpResponse("Invalid token payload", status=401)
        user = await sync_to_async(User.objects.get)(pk=user_id)
    except (TokenError, User.DoesNotExist):
        return HttpResponse("Invalid token", status=401)

    async def event_stream():
        # В этой точке await сигнализирует что операция занимает какое-то время
        # В этой точке мы идем заниматься своими вещами, когда мы получаем отсюда сообщение что "готово", то продолжаем с этого места
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            'notifications',
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

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
