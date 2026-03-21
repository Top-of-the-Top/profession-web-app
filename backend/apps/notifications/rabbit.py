import json
import os
import logging
from typing import Any, Dict
import pika

logger = logging.getLogger(__name__)

NOTIFICATIONS_EXCHANGE = "notifications"
NOTIFICATIONS_EXCHANGE_TYPE = "topic"

def get_connection_parameters() -> pika.ConnectionParameters:
    # Параметры из окружения
    return pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "guest"),
            os.getenv("RABBITMQ_PASS", "guest")
        ),
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=3,
        retry_delay=2.0, # Увеличили задержку между попытками
    )

def publish_event(*, routing_key: str, payload: Dict[str, Any]) -> None:
    """
    Публикует событие. Вызывается из Celery.
    Использует BlockingConnection, так как Celery-воркеры работают синхронно.
    """
    connection = None
    try:
        connection = pika.BlockingConnection(get_connection_parameters())
        channel = connection.channel()

        channel.exchange_declare(
            exchange=NOTIFICATIONS_EXCHANGE,
            exchange_type=NOTIFICATIONS_EXCHANGE_TYPE,
            durable=True,
        )

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        channel.basic_publish(
            exchange=NOTIFICATIONS_EXCHANGE,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to publish event to RabbitMQ: {e}")
        raise e
    finally:
        if connection and not connection.is_closed:
            connection.close()