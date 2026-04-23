from apps.courses.models import Course, Lesson
from ..models import Webinar, Recording
from .utils.agora_utils import (
    generate_rtc_token, user_uid_from_uuid, create_whiteboard_room,
    generate_whiteboard_room_token, recording_acquire, recording_start,
    recording_start_web, recording_stop, recording_stop_web,
    verify_recorder_token, make_recorder_token, ban_whiteboard_room,
    ROLE_PUBLISHER, ROLE_SUBSCRIBER,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser
from django.core.cache import caches
from django.utils import timezone
import os
import logging

logger = logging.getLogger(__name__)

def _stop_recording(recording):
    webinar = recording.webinar
    if recording.resource_id and recording.sid:
        try:
            result = recording_stop_web(
                channel_name=webinar.agora_channel_name,
                uid='1',
                resource_id=recording.resource_id,
                sid=recording.sid,
            )
            ext_state = result.get('serverResponse', {}).get('extensionServiceState', [])
            if ext_state:
                file_list = ext_state[0].get('payload', {}).get('fileList', [])
                if file_list:
                    recording.recording_url = file_list[0].get('fileName', '')
        except Exception:
            logger.exception("Ошибка остановки записи %s", recording.recording_id)

    recording.status = Recording.PROCESSING_STATUS
    recording.ended_at = timezone.now()
    recording.save(update_fields=['status', 'ended_at', 'recording_url', 'updated_at'])

    if recording.recording_url:
        from ..tasks import upload_recording_to_kinescope
        
        recording.kinescope_upload_status = 'pending'
        recording.save(update_fields=['kinescope_upload_status', 'updated_at'])
        upload_recording_to_kinescope.delay(str(recording.recording_id))


class WebinarStartView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(
                {'detail': 'Только автор курса/админ может запускать вебинар'},
                status=status.HTTP_403_FORBIDDEN,
            )

        webinar, _ = Webinar.objects.get_or_create(
            lesson=lesson,
            defaults={'started_by': request.user},
        )

        if webinar.status == Webinar.LIVE_STATUS:
            return Response(
                {'detail': 'Вебинар уже запущен'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_room_uuid = webinar.whiteboard_room_uuid
        try:
            webinar.whiteboard_room_uuid = create_whiteboard_room()
        except Exception:
            return Response(
                {'detail': 'Не удалось создать комнату доски'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if old_room_uuid:
            try:
                ban_whiteboard_room(old_room_uuid)
            except Exception:
                logger.warning('Не удалось забанить старую доску %s', old_room_uuid)

        webinar.status = Webinar.LIVE_STATUS
        webinar.started_by = request.user
        webinar.started_at = timezone.now()
        webinar.ended_at = None
        webinar.save()

        return Response({'detail': 'Вебинар запущен', 'webinar_id': str(webinar.webinar_id)})
    

class WebinarStopView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(
                {'detail': 'Только автор курса/админ может останавливать вебинар'},
                status=status.HTTP_403_FORBIDDEN,
            )

        webinar = get_object_or_404(Webinar, lesson=lesson)

        active_recording = webinar.recordings.filter(status=Recording.RECORDING_STATUS).first()
        if active_recording:
            _stop_recording(active_recording)

        if webinar.whiteboard_room_uuid:
            try:
                ban_whiteboard_room(webinar.whiteboard_room_uuid)
            except Exception:
                logger.warning('Не удалось забанить доску %s', webinar.whiteboard_room_uuid)

        webinar.status = Webinar.ENDED_STATUS
        webinar.ended_at = timezone.now()
        webinar.save(update_fields=['status', 'ended_at', 'updated_at'])

        return Response({'detail': 'Вебинар завершен'})


class WebinarJoinView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course

        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        is_teacher = is_author or is_moderator
        is_student = request.user.is_enrolled(course)

        if not is_teacher and not is_student:
            return Response(
                {'detail': 'Нет доступа к вебинару'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        try:
            webinar = Webinar.objects.get(lesson=lesson, status='live')
        except Webinar.DoesNotExist:
            return Response(
                {'detail': 'Вебинар не запущен'},
                status=status.HTTP_404_NOT_FOUND,
            )

        uid = user_uid_from_uuid(request.user.pk)
        rtc_role = ROLE_PUBLISHER
        whiteboard_role = 'admin' if is_teacher else 'writer'
        user_role = 'teacher' if is_teacher else 'student'

        rtc_token = generate_rtc_token(
            channel_name=webinar.agora_channel_name,
            uid=uid,
            role=rtc_role,
        )

        whiteboard_room_token = generate_whiteboard_room_token(
            room_uuid=webinar.whiteboard_room_uuid,
            role=whiteboard_role,
        )

        return Response({
            'rtc_token': rtc_token,
            'agora_app_id': os.getenv('AGORA_APP_ID'),
            'channel_name': webinar.agora_channel_name,
            'uid': uid,
            'whiteboard_app_id': os.getenv('AGORA_WHITEBOARD_APP_ID'),
            'whiteboard_room_uuid': webinar.whiteboard_room_uuid,
            'whiteboard_room_token': whiteboard_room_token,
            'whiteboard_region': os.getenv('AGORA_WHITEBOARD_REGION', 'eu'),
            'role': user_role,
        })


class WebinarRecorderJoinView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, course_slug, lesson_slug):
        token = request.query_params.get('token', '')
        if not token:
            return Response({'detail': 'Token required'}, status=status.HTTP_400_BAD_REQUEST)

        webinar_id = verify_recorder_token(token)
        if not webinar_id:
            return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_403_FORBIDDEN)

        webinar = get_object_or_404(
            Webinar,
            webinar_id=webinar_id,
            lesson__slug=lesson_slug,
            lesson__section__course__slug=course_slug,
            status='live',
        )

        recorder_uid = 999999
        rtc_token = generate_rtc_token(webinar.agora_channel_name, recorder_uid, ROLE_SUBSCRIBER)
        wb_token = generate_whiteboard_room_token(webinar.whiteboard_room_uuid, 'reader')

        return Response({
            'rtc_token': rtc_token,
            'agora_app_id': os.getenv('AGORA_APP_ID'),
            'channel_name': webinar.agora_channel_name,
            'uid': recorder_uid,
            'whiteboard_app_id': os.getenv('AGORA_WHITEBOARD_APP_ID'),
            'whiteboard_room_uuid': webinar.whiteboard_room_uuid,
            'whiteboard_room_token': wb_token,
            'whiteboard_region': os.getenv('AGORA_WHITEBOARD_REGION', 'eu'),
            'role': 'recorder',
        })


class WebinarRecordingStartView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(status=status.HTTP_403_FORBIDDEN)

        webinar = get_object_or_404(Webinar, lesson=lesson, status=Webinar.LIVE_STATUS)
        
        if webinar.recordings.filter(status=Recording.RECORDING_STATUS).exists():
            return Response({'detail': 'Запись уже идет'}, status=status.HTTP_400_BAD_REQUEST)
        
        recording = Recording.objects.create(
            webinar=webinar,
            started_by=request.user,
            status=Recording.RECORDING_STATUS,
            started_at=timezone.now(),
        )
        recording_uid = '1'
        token = make_recorder_token(str(webinar.webinar_id))
        frontend_base = os.getenv('FRONTEND_BASE_URL', 'https://professionkid.ru')
        recorder_url = f"{frontend_base}/webinar-record/{course_slug}/{lesson_slug}?token={token}"

        resource_id = recording_acquire(
            channel_name=webinar.agora_channel_name,
            uid=recording_uid,
            scene=1,
        )
        sid = recording_start_web(
            channel_name=webinar.agora_channel_name,
            uid=recording_uid,
            resource_id=resource_id,
            recorder_url=recorder_url,
        )

        recording.resource_id = resource_id
        recording.sid = sid
        recording.save(update_fields=['resource_id', 'sid', 'updated_at'])
        
        return Response({'detail': 'Запись началась', 'recording_id': str(recording.recording_id)})


class WebinarRecordingStopView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(
                {'detail': 'Только автор курса/админ может останавливать запись'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        webinar = get_object_or_404(Webinar, lesson=lesson, status=Webinar.LIVE_STATUS)
        recording = webinar.recordings.filter(status=Recording.RECORDING_STATUS).first()
        if not recording:
            return Response({'detail': 'Запись не идет'}, status=status.HTTP_400_BAD_REQUEST)

        _stop_recording(recording)

        return Response({'detail': 'Запись остановлена', 'recording_id': str(recording.recording_id)})


class RecordingPdfView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    def post(self, request, course_slug, lesson_slug, recording_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(status=status.HTTP_403_FORBIDDEN)

        recording = get_object_or_404(
            Recording,
            recording_id=recording_id,
            webinar__lesson=lesson,
            is_deleted=False,
        )

        screenshots = request.FILES.getlist('screenshots')
        if not screenshots:
            return Response(
                {'detail': "Нет скриншотов"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import img2pdf
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage

        images = [f.read() for f in screenshots]
        pdf_bytes = img2pdf.convert(images)

        pdf_path = f'whiteboards/recording_{recording.recording_id}.pdf'
        saved_path = default_storage.save(pdf_path, ContentFile(pdf_bytes))

        bucket = os.getenv('AWS_S3_BUCKET_NAME')
        recording.whiteboard_pdf_url = (f'https://storage.yandexcloud.net/{bucket}/{saved_path}')
        recording.save(update_fields=['whiteboard_pdf_url', 'updated_at'])

        return Response({'detail': 'pdf доски сохранен'})

    def delete(self, request, course_slug, lesson_slug, recording_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(
                {'detail': 'Только автор курса/админ может удалять pdf доски'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        recording = get_object_or_404(
            Recording,
            recording_id=recording_id,
            webinar__lesson=lesson,
            is_deleted=False,
        )
        if not recording.whiteboard_pdf_url:
            return Response({'detail': 'PDF не привязан'}, status=status.HTTP_404_NOT_FOUND)

        recording.whiteboard_pdf_url = ''
        recording.save(update_fields=['whiteboard_pdf_url', 'updated_at'])
        
        return Response({'detail': 'pdf доски удален'}, status=status.HTTP_204_NO_CONTENT)
    

class RecordingDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, course_slug, lesson_slug, recording_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        is_author = course.authors.filter(pk=request.user.pk).exists()
        is_moderator = request.user.is_moderator()
        if not is_author and not is_moderator:
            return Response(
                {'detail': 'Только автор курса/админ может удалять запись'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        recording = get_object_or_404(
            Recording,
            recording_id=recording_id,
            webinar__lesson=lesson,
            is_deleted=False,
        )
        recording.is_deleted = True
        recording.deleted_at = timezone.now()
        recording.deleted_by = request.user
        recording.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
        
        return Response({'detail': 'запись удалена'}, status=status.HTTP_204_NO_CONTENT)


class KinescopeDRMAuthView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        import base64 as b64
        import jwt
        from django.conf import settings as django_settings
        from apps.users.models import User

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        expected_user = os.getenv('KINESCOPE_DRM_AUTH_USERNAME', '')
        expected_pass = os.getenv('KINESCOPE_DRM_AUTH_PASSWORD', '')

        if not self._verify_basic_auth(auth_header, expected_user, expected_pass):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        video_id = request.data.get('id', '')
        drm_token = request.data.get('token', '')

        if not video_id or not drm_token:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        try:
            payload = jwt.decode(
                drm_token,
                django_settings.SECRET_KEY,
                algorithms=['HS256'],
            )
            user_id = payload.get('user_id')
            token_video_id = payload.get('video_id')
        except Exception:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if token_video_id != video_id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        try:
            recording = Recording.objects.select_related(
                'webinar__lesson__section__course'
            ).get(kinescope_video_id=video_id, is_deleted=False)
        except Recording.DoesNotExist:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            user = User.objects.get(pk=user_id)
            course = recording.webinar.lesson.section.course
            if user.is_enrolled(course) or course.authors.filter(pk=user.pk).exists():
                return Response(status=status.HTTP_200_OK)
        except User.DoesNotExist:
            pass

        return Response(status=status.HTTP_403_FORBIDDEN)
    
    @staticmethod
    def _verify_basic_auth(auth_header, expected_user, expected_pass):
        import base64 as b64

        if not auth_header.startswith('Basic '):
            return False
        try:
            decoded = b64.b64decode(auth_header[6:]).decode()
            username, password = decoded.split(':', 1)
            return username == expected_user and password == expected_pass
        except Exception:
            return False
        