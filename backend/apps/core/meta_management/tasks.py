import json
import logging
from urllib.parse import unquote_plus

from celery import shared_task
from django.conf import settings


logger = logging.getLogger(__name__)


PENDING_TTL_HOURS = 24
UNREFERENCED_GRACE_DAYS = 7
POLL_MAX_MESSAGES = 10


def _get_worker_api():
    from .factory import build_worker_api
    return build_worker_api()


@shared_task(bind=True, max_retries=3, default_retry_delay=5, acks_late=True)
def commit_pending_asset(self, asset_id):
    worker = _get_worker_api()
    try:
        worker.commit_by_id(asset_id)
        return {'status': 'ok', 'asset_id': str(asset_id)}
    except Exception as exc:
        logger.exception('commit_pending_asset: ошибка для %s', asset_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def delete_asset_from_storage(self, asset_id):
    worker = _get_worker_api()
    try:
        return worker.physical_delete(asset_id)
    except Exception as exc:
        logger.exception('delete_asset_from_storage: ошибка для %s', asset_id)
        raise self.retry(exc=exc)


@shared_task
def sweep_orphaned_assets():
    worker = _get_worker_api()
    orphaned_ids = worker.find_orphaned(grace_days=UNREFERENCED_GRACE_DAYS)

    for asset_id in orphaned_ids:
        delete_asset_from_storage.delay(str(asset_id))

    return {'scheduled': len(orphaned_ids)}


@shared_task
def sweep_pending_assets():
    worker = _get_worker_api()
    return worker.sweep_pending(pending_ttl_hours=PENDING_TTL_HOURS)


@shared_task
def poll_s3_upload_events():
    queue_url = getattr(settings, 'ASSET_S3_EVENT_QUEUE_URL', '')
    if not queue_url:
        return {'status': 'disabled'}

    import boto3
    from botocore.exceptions import ClientError

    try:
        client = boto3.client(
            'sqs',
            endpoint_url=getattr(settings, 'ASSET_S3_EVENT_QUEUE_ENDPOINT', 'https://message-queue.api.cloud.yandex.net'),
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'ru-central1'),
        )
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=POLL_MAX_MESSAGES,
            WaitTimeSeconds=0,
            VisibilityTimeout=60,
        )
    except ClientError:
        logger.exception('poll_s3_upload_events: ошибка подключения к YMQ')
        return {'status': 'error'}

    messages = response.get('Messages') or []
    if not messages:
        return {'status': 'empty'}

    worker = _get_worker_api()
    processed = 0

    for message in messages:
        receipt = message.get('ReceiptHandle')
        body = message.get('Body') or '{}'

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning('poll_s3_upload_events: невалидный JSON: %s', body[:200])
            client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            continue

        records = payload.get('Records') or payload.get('messages') or []

        for record in records:
            s3_block = record.get('s3') or {}
            object_block = s3_block.get('object') or {}
            raw_key = object_block.get('key')
            if not raw_key:
                continue

            key = unquote_plus(raw_key)

            try:
                result = worker.commit_by_storage_key(key, backend='s3')
                if result is not None:
                    processed += 1
            except Exception:
                logger.exception('poll_s3_upload_events: commit failed для %s', key)

        try:
            client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
        except ClientError:
            logger.exception('poll_s3_upload_events: не удалось удалить сообщение')

    return {'status': 'ok', 'processed': processed, 'received': len(messages)}
