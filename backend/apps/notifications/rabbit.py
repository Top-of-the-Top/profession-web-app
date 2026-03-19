import json
import os
from typing import Any, Dict
import pika

# Настроили тематическую рассылку: поменяли fanout на topic и имя на notifications.group
NOTIFICATIONS_EXCHANGE = "notifications.group"
NOTIFICATIONS_EXCHANGE_TYPE = "topic"


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


def publish_event(*, routing_key: str, payload: Dict[str, Any]) -> None:
    """
    Публикует событие с использованием тематической маршрутизации (topic).
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
        routing_key=routing_key, # Теперь используем ключ (напр. "user.1" или "course.5")
        body=body,
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2, # Сообщение станет устойчивым к перезагрузкам брокера
        ),
    )

    connection.close()