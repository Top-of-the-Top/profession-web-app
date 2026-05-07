import asyncio
import json
import logging

import aio_pika
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponse, HttpResponseNotAllowed, StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User

from ..models import Notification
from .serializers import NotificationSerializer

RABBITMQ_CONNECT_RETRIES = 5
RABBITMQ_RETRY_DELAY = 2

logger = logging.getLogger(__name__)


def _user_notifications_qs(user):
    Through = Notification.read_by.through
    purchased_course_ids = user.get_purchased_courses_ids()
    return (
        Notification.objects.filter(
            Q(user=user)
            | Q(course_id__in=purchased_course_ids)
            | Q(notification_type=Notification.SYSTEM)
        )
        .distinct()
        .annotate(
            is_read=Exists(
                Through.objects.filter(
                    notification_id=OuterRef("pk"),
                    user_id=user.pk,
                )
            )
        )
    )


PAGE_SIZE = 20


@extend_schema(
    tags=["Notifications"],
    summary="Список уведомлений пользователя",
    parameters=[
        OpenApiParameter(
            name="before_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Вернуть уведомления с id строго меньше указанного (курсор пагинации)",
        ),
    ],
    responses={200: NotificationSerializer(many=True)},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications_for_user(request):
    qs = _user_notifications_qs(request.user)

    before_id = request.GET.get("before_id")
    if before_id:
        try:
            qs = qs.filter(id__lt=int(before_id))
        except (ValueError, TypeError):
            logger.debug(
                "Invalid before_id query parameter: %r; skipping cursor filter",
                before_id,
            )

    page = list(qs[: PAGE_SIZE + 1])
    has_more = len(page) > PAGE_SIZE

    serializer = NotificationSerializer(page[:PAGE_SIZE], many=True)
    return Response({"results": serializer.data, "has_more": has_more})


@extend_schema(
    tags=["Notifications"],
    summary="Пометить все уведомления пользователя как прочитанные",
    responses={200: {"description": '{"marked": int}', "content": {"application/json": {}}}},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    user = request.user
    Through = Notification.read_by.through

    unread_ids = list(
        _user_notifications_qs(user).filter(is_read=False).values_list("id", flat=True)
    )

    if unread_ids:
        Through.objects.bulk_create(
            [Through(notification_id=n_id, user_id=user.pk) for n_id in unread_ids],
            ignore_conflicts=True,
        )

    return Response({"marked": len(unread_ids)})


@extend_schema(
    tags=["Notifications"],
    summary="Поток уведомлений (SSE)",
    description="Server-Sent Events; требуется query-параметр token (JWT access).",
    parameters=[
        OpenApiParameter(
            name="token",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=True,
            description="JWT access token",
        ),
    ],
    responses={
        200: {
            "description": "Поток text/event-stream",
            "content": {"text/event-stream": {}},
        },
        401: {"description": "Нет или неверный token"},
    },
)
async def sse_notifications(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    token = request.GET.get("token")
    if not token:
        return HttpResponse("Missing token", status=401)

    try:
        access_token = AccessToken(token)
        user_id = access_token.get("user_id")
        if not user_id:
            return HttpResponse("Invalid token payload", status=401)
        user = await sync_to_async(User.objects.get, thread_sensitive=False)(pk=user_id)
    except (TokenError, User.DoesNotExist):
        return HttpResponse("Invalid token", status=401)

    webinar_id = request.GET.get("webinar_id")

    user_pk = user.pk
    get_course_ids = sync_to_async(
        lambda: list(user.get_purchased_courses_ids()),
        thread_sensitive=False,
    )
    user_course_ids = await get_course_ids()

    async def event_stream():
        connection = None

        for attempt in range(1, RABBITMQ_CONNECT_RETRIES + 1):
            try:
                connection = await aio_pika.connect_robust(
                    settings.RABBITMQ_URL,
                    timeout=10,
                )
                break
            except Exception as exc:
                logger.warning("SSE: RabbitMQ подключение #%d не удалось: %s", attempt, exc)
                if attempt < RABBITMQ_CONNECT_RETRIES:
                    await asyncio.sleep(RABBITMQ_RETRY_DELAY)
                else:
                    logger.error(
                        "SSE: RabbitMQ недоступен после %d попыток",
                        RABBITMQ_CONNECT_RETRIES,
                    )
                    yield b'event: error\ndata: {"detail": "broker_unavailable"}\n\n'
                    return

        try:
            channel = await connection.channel()

            exchange = await channel.declare_exchange(
                "notifications",
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            queue = await channel.declare_queue(exclusive=True)
            await queue.bind(exchange, routing_key=f"user.{user_pk}")

            for c_id in user_course_ids:
                await queue.bind(exchange, routing_key=f"course.{c_id}")

            await queue.bind(exchange, routing_key="system.all")

            if webinar_id:
                await queue.bind(exchange, routing_key=f"webinar.{webinar_id}")

            async with queue.iterator() as queue_iter:
                yield b": heartbeat\n\n"
                async for message in queue_iter:
                    async with message.process():
                        data = json.loads(message.body.decode())
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")

        except Exception as exc:
            logger.warning("SSE: ошибка в потоке уведомлений для user=%s: %s", user_pk, exc)
        finally:
            if connection and not connection.is_closed:
                await connection.close()

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
