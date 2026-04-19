import logging
import os
from celery import shared_task
import time as time_module

logger = logging.getLogger(__name__)

S3_BASE_URL = 'https://storage.yandexcloud.net'


@shared_task
def check_idle_webinars():
    from .models import Webinar
    from .api.utils.agora_utils import get_channel_user_count, recording_stop_web, ban_whiteboard_room
    from django.core.cache import caches
    from django.utils import timezone

    cache = caches['default']
    idle_threshold = 300

    for webinar in Webinar.objects.filter(status='live'):
        cache_key = f'webinar_empty_since:{webinar.webinar_id}'

        try:
            user_count = get_channel_user_count(webinar.agora_channel_name)
        except Exception:
            logger.exception('Не удалось запросить агору для канала %s', webinar.agora_channel_name)
            continue
            
        if user_count > 0:
            cache.delete(cache_key)
            continue

        empty_since = cache.get(cache_key)

        if empty_since is None:
            cache.set(cache_key, time_module.time(), timeout=300)
            logger.info('Вебинар %s: канал пустой, начинаем отсчет', webinar.webinar_id)
            continue
            
        elapsed = time_module.time() - empty_since
        if elapsed < idle_threshold:
            continue

        logger.info('Автоостановка вебинара %s, тк канал пуст %d секунд', webinar.webinar_id, int(elapsed))

        if webinar.recording_resource_id and webinar.recording_sid:
            try:
                result = recording_stop_web(
                    channel_name=webinar.agora_channel_name,
                    uid='1',
                    resource_id=webinar.recording_resource_id,
                    sid=webinar.recording_sid,
                )
                server_response = result.get('serverResponse', {})
                ext_state = server_response.get('extensionServiceState', [])
                if ext_state:
                    payload = ext_state[0].get('payload', {})
                    file_list = payload.get('fileList', [])
                    if file_list:
                        webinar.recording_url = file_list[0].get('fileName', '')
            except Exception:
                logger.exception('Ошибка остановки записи для %s', webinar.webinar_id)

            webinar.status = 'ended'
            webinar.ended_at = timezone.now()
            webinar.save()

            if webinar.recording_url:
                webinar.kinescope_upload_status = 'pending'
                webinar.save(update_fields=['kinescope_upload_status'])
                upload_recording_to_kinescope.delay(str(webinar.webinar_id))
                
            cache.delete(cache_key)

            if webinar.whiteboard_room_uuid:
                try:
                    ban_whiteboard_room(webinar.whiteboard_room_uuid)
                except Exception:
                    logger.exception('Ошибка бана комнаты %s', webinar.whiteboard_room_uuid)


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
    
    recording_url = webinar.recording_url
    if not recording_url.startswith('http'):
        bucket = os.getenv('AWS_S3_BUCKET_NAME', 'profession-web-app')
        recording_url = f'{S3_BASE_URL}/{bucket}/{recording_url}'

    course = webinar.lesson.section.course
    if not course.kinescope_folder_id:
        folder_id = create_folder(name=course.title)
        course.kinescope_folder_id = folder_id
        course.save(update_fields=['kinescope_folder_id', 'updated_at'])
        logger.info('Создана папка Kinescope "%s" (id=%s) для курса %s',
            course.title, folder_id, course.course_id,
        )

    title = f'Вебинар: {webinar.lesson.title}'

    webinar.kinescope_upload_status = 'uploading'
    webinar.save(update_fields=['kinescope_upload_status', 'updated_at'])

    try:
        result = upload_video_by_url(
            video_url=recording_url,
            title=title,
            parent_id=course.kinescope_folder_id,
        )
        video_id = result.get('id', '')

        webinar.kinescope_video_id = video_id
        webinar.kinescope_upload_status = 'processing'
        webinar.save(update_fields=['kinescope_video_id', 'kinescope_upload_status', 'updated_at'])

        check_kinescope_processing.apply_async(
            args=[str(webinar.webinar_id)],
            countdown=30,
        )

        return {'status': 'uploaded', 'video_id': video_id}
    
    except Exception as exc:
        webinar.kinescope_upload_status = 'failed'
        webinar.save(update_fields=['kinescope_upload_status', 'updated_at'])

        logger.error(
            'Kinescope upload failed для webinar %s: %s', webinar_id, exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=20,
    default_retry_delay=30,
    acks_late=True,
)
def check_kinescope_processing(self, webinar_id):
    from .models import Webinar
    from .api.utils.kinescope_utils import get_video_status

    try:
        webinar = Webinar.objects.get(webinar_id=webinar_id)
    except Webinar.DoesNotExist:
        return {'status': 'error', 'detail': 'Webinar not found'}
    
    if not webinar.kinescope_video_id:
        return {'status': 'error', 'detail': 'No video id'}
    
    try:
        video_data = get_video_status(webinar.kinescope_video_id)
        video_status = video_data.get('status', '')

        if video_status == 'ready':
            webinar.kinescope_upload_status = 'ready'
            webinar.save(update_fields=['kinescope_upload_status', 'updated_at'])
            return {'status': 'ready'}
        
        if video_status in ('error', 'failed'):
            webinar.kinescope_upload_status = 'failed'
            webinar.save(update_fields=['kinescope_upload_status', 'updated_at'])
            logger.error('Kinescope processing failed для webinar %s: %s', webinar_id, video_status)
            return {'status': 'failed'}

        raise self.retry()
    
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        webinar.kinescope_upload_status = 'failed'
        webinar.save(update_fields=['kinescope_upload_status', 'updated_at'])
        logger.error('Kinescope status check timed out для webinar %s: %s', webinar_id, exc)
        return {'status': 'timeout'}
