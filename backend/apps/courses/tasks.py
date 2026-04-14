import logging
import os
from celery import shared_task

logger = logging.getLogger(__name__)

S3_BASE_URL = 'https://storage.yandexcloud.net'


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def upload_recording_to_kinescope(self, webinar_id):
    from .models import Webinar
    from .api.utils.kinescope_utils import upload_video_by_url, create_folder

    try:
        webinar = Webinar.objects.select_related('lesson__section__course').get(webinar_id=webinar_id)
    except Webinar.DoesNotExist:
        logger.error('Webinar %s не найден', webinar_id)
        return {'status': 'error', 'detail': f'Webinar {webinar_id} not found'}
    
    if not webinar.recording_url:
        logger.warning('Webinar %s: нет recording_url', webinar_id)
        return {'status': 'skipped', 'detail': 'No recording URL'}
    
    if webinar.kinescope_video_id:
        logger.info('Webinar %s: уже загружен в Kinescope', webinar_id)
        return {'status': 'skipped', 'detail': 'Already uploaded'}
