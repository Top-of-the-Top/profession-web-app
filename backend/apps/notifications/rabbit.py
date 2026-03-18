import json
import os
from typing import Any, Dict
import pika

# TODO: настроить тематическую рассылку по очередям, то есть поменять fanout на topic и NOTIFICATIONS_EXCHANGE на group
NOTIFICATIONS_EXCHANGE = "notifications.broadcast"
NOTIFICATIONS_EXCHANGE_TYPE = "fanout"


def get_connection_parameters() -> pika.ConnectionParameters:
    # Вытягиваем настройки нашего RabbitMQ из settings
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    username = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    return pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=pika.PlainCredentials(username, password),
        heartbeat=30, # каждые 30 секунд обмен сигналами между кодом и реальным rabbitmq
        blocked_connection_timeout=30, # Если кончилась память в брокере при пиковых нагрузках, то можем подождать 30 секунд
        connection_attempts=3, # Попыток достучаться дл брокера
        retry_delay=1.0,
        socket_timeout=5.0,
    )


def publish_broadcast_event(*, payload: Dict[str, Any]) -> None:
    """
    Публикует одно событие для всех подписчиков (fanout).
    """
    connection = pika.BlockingConnection(get_connection_parameters()) # Это одно TCP соединение front - back
    channel = connection.channel() # А это канал внутри TCP соединения

    channel.exchange_declare(
        exchange=NOTIFICATIONS_EXCHANGE,
        exchange_type=NOTIFICATIONS_EXCHANGE_TYPE,
        durable=True,
    )

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    channel.basic_publish(
        exchange=NOTIFICATIONS_EXCHANGE,
        routing_key="",
        body=body,
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=1,
        ),
    )

    connection.close()
