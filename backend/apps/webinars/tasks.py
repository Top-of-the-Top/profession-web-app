import logging
import os
from celery import shared_task
import time as time_module

logger = logging.getLogger(__name__)

S3_BASE_URL = 'https://storage.yandexcloud.net'


@shared_task
def check_idle_webinars():
    from .models import Webinar
    from django.core.cache import caches

    cache = caches['default']
    for webinar in Webinar.objects.filter(status=Webinar.LIVE_STATUS):
        _process_idle_webinar(webinar, cache)


def _process_idle_webinar(webinar, cache):
    from .api.utils.agora_utils import get_channel_user_count, ban_whiteboard_room
    from .api.views import _stop_recording
    from .models import Recording
    from django.utils import timezone

    IDLE_THRESHOLD = 300
    cache_key = f'webinar_empty_since:{webinar.webinar_id}'

    try:
        user_count = get_channel_user_count(webinar.agora_channel_name)
    except Exception:
        logger.exception('Не удалось запросить агору для канала %s', webinar.agora_channel_name)
        return

    if user_count > 0:
        cache.delete(cache_key)
        return

    empty_since = cache.get(cache_key)
    if empty_since is None:
        cache.set(cache_key, time_module.time(), timeout=300)
        logger.info('Вебинар %s: канал пустой, начинаем отсчет', webinar.webinar_id)
        return

    elapsed = time_module.time() - empty_since
    if elapsed < IDLE_THRESHOLD:
        return

    logger.info('Автоостановка вебинара %s, тк канал пуст %d секунд', webinar.webinar_id, int(elapsed))

    active = webinar.recordings.filter(status=Recording.RECORDING_STATUS).first()
    if active:
        _stop_recording(active)

    if webinar.whiteboard_room_uuid:
        try:
            ban_whiteboard_room(webinar.whiteboard_room_uuid)
        except Exception:
            logger.warning('Не удалось забанить доску %s при idle-стопе', webinar.whiteboard_room_uuid)

    webinar.status = 'ended'
    webinar.ended_at = timezone.now()
    webinar.save(update_fields=['status', 'ended_at', 'updated_at'])
    cache.delete(cache_key)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def upload_recording_to_kinescope(self, recording_id):
    from .models import Recording
    from .api.utils.kinescope_utils import upload_video_by_url, create_folder

    try:
        recording = Recording.objects.select_related('webinar__lesson__section__course').get(recording_id=recording_id)
    except Recording.DoesNotExist:
        logger.error('Recording %s не найден', recording_id)
        return {'status': 'error', 'detail': f'Recording {recording_id} not found'}
    
    if not recording.recording_url:
        logger.warning('Recording %s: нет recording_url', recording_id)
        return {'status': 'skipped', 'detail': 'No recording URL'}
    
    if recording.kinescope_video_id:
        logger.info('Recording %s: уже загружен в Kinescope', recording_id)
        return {'status': 'skipped', 'detail': 'Already uploaded'}
    
    recording_url = recording.recording_url
    if not recording_url.startswith('http'):
        bucket = os.getenv('AWS_S3_BUCKET_NAME', 'profession-web-app')
        if not recording_url.startswith('recordings/'):
            recording_url = f'recordings/webinars/{recording_url}'
        recording_url = f'{S3_BASE_URL}/{bucket}/{recording_url}'

    logger.info('Recording %s: URL для Kinescope: %s', recording_id, recording_url)

    course = recording.webinar.lesson.section.course
    if not course.kinescope_folder_id:
        folder_id = create_folder(name=course.title)
        course.kinescope_folder_id = folder_id
        course.save(update_fields=['kinescope_folder_id', 'updated_at'])
        logger.info('Создана папка Kinescope "%s" (id=%s) для курса %s',
            course.title, folder_id, course.course_id,
        )

    title = f'Вебинар: {recording.webinar.lesson.title} ({recording.started_at:%d.%m.%Y %H:%M})'

    recording.kinescope_upload_status = 'uploading'
    recording.save(update_fields=['kinescope_upload_status', 'updated_at'])

    try:
        result = upload_video_by_url(
            video_url=recording_url,
            title=title,
            parent_id=course.kinescope_folder_id,
        )
        video_id = result.get('id', '')

        recording.kinescope_video_id = video_id
        recording.kinescope_upload_status = 'processing'
        recording.save(update_fields=['kinescope_video_id', 'kinescope_upload_status', 'updated_at'])

        check_kinescope_processing.apply_async(
            args=[str(recording.recording_id)],
            countdown=30,
        )

        return {'status': 'uploaded', 'video_id': video_id}
    
    except Exception as exc:
        recording.kinescope_upload_status = 'failed'
        recording.save(update_fields=['kinescope_upload_status', 'updated_at'])
        logger.error(
            'Не удалось загрузить в Kinescope для recording %s: %s', recording_id, exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=20,
    default_retry_delay=30,
    acks_late=True,
)
def check_kinescope_processing(self, recording_id):
    from .models import Recording
    from .api.utils.kinescope_utils import get_video_status

    try:
        recording = Recording.objects.get(recording_id=recording_id)
    except Recording.DoesNotExist:
        return {'status': 'error', 'detail': 'Recording not found'}
    
    if not recording.kinescope_video_id:
        return {'status': 'error', 'detail': 'No video id'}
    
    try:
        video_data = get_video_status(recording.kinescope_video_id)
        video_status = video_data.get('status', '')

        if video_status == Recording.READY_STATUS:
            recording.kinescope_upload_status = Recording.READY_STATUS
            recording.save(update_fields=['kinescope_upload_status', 'updated_at'])
            return {'status': Recording.READY_STATUS}
        
        if video_status in ('error', 'failed'):
            recording.kinescope_upload_status = Recording.FAILED_STATUS
            recording.save(update_fields=['kinescope_upload_status', 'updated_at'])
            logger.error('Ошибка обработки Kinescope для recording %s: %s', recording_id, video_status)
            return {'status': Recording.FAILED_STATUS}

        raise self.retry()
    
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        recording.kinescope_upload_status = Recording.FAILED_STATUS
        recording.save(update_fields=['kinescope_upload_status', 'updated_at'])
        logger.error('Таймаут проверки статуса Kinescope для recording %s: %s', recording_id, exc)
        return {'status': 'timeout'}
