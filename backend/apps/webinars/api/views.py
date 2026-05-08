import logging
import os

import img2pdf
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.meta_management.errors import AssetError
from apps.core.meta_management.factory import build_binding_api, build_upload_api
from apps.core.processors.error_processor import process_error_response
from apps.courses.api.permissions import require_course_author, require_course_enrollment
from apps.courses.api.utils.cache_utils import invalidate_lesson_detail_cache
from apps.courses.models import Lesson

from ..models import Recording, Webinar
from .schema import SCHEMA_DETAIL
from .serializers import (
    DetailResponseSerializer,
    WebinarRecordingStartResponseSerializer,
    WebinarScheduleRequestSerializer,
    WebinarScheduleResponseSerializer,
    WebinarStartResponseSerializer,
    WebinarTokenSerializer,
)
from .utils.agora_utils import (
    ROLE_PUBLISHER,
    ROLE_SUBSCRIBER,
    ban_whiteboard_room,
    create_whiteboard_room,
    generate_rtc_token,
    generate_rtm_token,
    generate_whiteboard_room_token,
    make_recorder_token,
    recording_acquire,
    recording_start_web,
    recording_stop_web,
    user_uid_from_uuid,
    verify_recorder_token,
)

logger = logging.getLogger(__name__)


def _pick_filename(file_entry):
    if isinstance(file_entry, dict):
        return file_entry.get("fileName", "") or file_entry.get("filename", "")
    if isinstance(file_entry, str):
        return file_entry
    return ""


def _extract_recording_url(agora_response):
    sr = agora_response.get("serverResponse", {})

    candidates = []

    ext_state = sr.get("extensionServiceState", [])
    if isinstance(ext_state, list):
        for service in ext_state:
            files = (
                service.get("payload", {}).get("fileList", []) if isinstance(service, dict) else []
            )
            if isinstance(files, list):
                for f in files:
                    name = _pick_filename(f)
                    if name:
                        candidates.append(name)

    file_list = sr.get("fileList", [])
    if isinstance(file_list, list):
        for f in file_list:
            name = _pick_filename(f)
            if name:
                candidates.append(name)

    single = sr.get("fileName", "") or sr.get("filename", "")
    if single:
        candidates.append(single)

    if not candidates:
        return ""

    for name in candidates:
        if name.lower().endswith(".mp4"):
            return name

    return candidates[0]


def _stop_recording(recording):
    webinar = recording.webinar
    if recording.resource_id and recording.sid:
        try:
            result = recording_stop_web(
                channel_name=webinar.agora_channel_name,
                uid="1",
                resource_id=recording.resource_id,
                sid=recording.sid,
            )
            logger.info(
                "Agora stop_web ответ для записи %s: %s",
                recording.recording_id,
                result,
            )
            recording_url = _extract_recording_url(result)
            if recording_url:
                recording.recording_url = recording_url
                logger.info(
                    "Извлечен recording_url для записи %s: %s",
                    recording.recording_id,
                    recording_url,
                )
            else:
                logger.error(
                    "Не удалось извлечь recording_url из ответа Agora для записи %s. Ответ: %s",
                    recording.recording_id,
                    result,
                )
        except Exception:
            logger.exception("Ошибка остановки записи %s", recording.recording_id)

    recording.status = Recording.PROCESSING_STATUS
    recording.ended_at = timezone.now()
    recording.save(update_fields=["status", "ended_at", "recording_url", "updated_at"])

    if recording.recording_url:
        from ..tasks import upload_recording_to_kinescope

        recording.kinescope_upload_status = "pending"
        recording.save(update_fields=["kinescope_upload_status", "updated_at"])
        upload_recording_to_kinescope.delay(str(recording.recording_id))
    else:
        logger.warning(
            "Запись %s остается в processing без recording_url, kinescope upload не запущен",
            recording.recording_id,
        )

    from apps.notifications.tasks import publish_event_async

    publish_event_async.delay(
        routing_key=f"webinar.{webinar.webinar_id}",
        payload={
            "type": "recording_stopped",
            "webinar_id": str(webinar.webinar_id),
            "recording_id": str(recording.recording_id),
            "ended_at": recording.ended_at.isoformat() if recording.ended_at else None,
        },
    )


@extend_schema_view(
    post=extend_schema(
        summary="Запустить вебинар",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: WebinarStartResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            502: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarStartView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        webinar, _ = Webinar.objects.get_or_create(
            lesson=lesson,
            defaults={"started_by": request.user},
        )

        if webinar.status == Webinar.LIVE_STATUS:
            return Response(
                {
                    "detail": "Вебинар уже запущен, поэтому запуск проигнорирован",
                    "webinar_id": str(webinar.webinar_id),
                }
            )

        old_room_uuid = webinar.whiteboard_room_uuid
        try:
            webinar.whiteboard_room_uuid = create_whiteboard_room()
        except Exception:
            return Response(
                {"detail": "Не удалось создать комнату доски"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if old_room_uuid:
            try:
                ban_whiteboard_room(old_room_uuid)
            except Exception:
                logger.warning("Не удалось забанить старую доску %s", old_room_uuid)

        webinar.status = Webinar.LIVE_STATUS
        webinar.started_by = request.user
        webinar.started_at = timezone.now()
        webinar.ended_at = None
        webinar.save()

        from apps.notifications.tasks import send_webinar_started_notification

        course = lesson.section.course
        send_webinar_started_notification.delay(
            course_id=str(course.course_id),
            lesson_id=str(lesson.lesson_id),
            course_slug=course.slug,
            lesson_slug=lesson.slug,
            course_title=course.title,
            lesson_title=lesson.title,
            webinar_id=str(webinar.webinar_id),
        )

        return Response({"detail": "Вебинар запущен", "webinar_id": str(webinar.webinar_id)})


@extend_schema_view(
    post=extend_schema(
        summary="Остановить вебинар",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: DetailResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarStopView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        webinar = get_object_or_404(Webinar, lesson=lesson)

        active_recording = webinar.recordings.filter(status=Recording.RECORDING_STATUS).first()
        if active_recording:
            _stop_recording(active_recording)

        if webinar.whiteboard_room_uuid:
            try:
                ban_whiteboard_room(webinar.whiteboard_room_uuid)
            except Exception:
                logger.warning("Не удалось забанить доску %s", webinar.whiteboard_room_uuid)

        webinar.status = Webinar.ENDED_STATUS
        webinar.ended_at = timezone.now()
        webinar.save(update_fields=["status", "ended_at", "updated_at"])

        from apps.notifications.tasks import publish_event_async

        publish_event_async.delay(
            routing_key=f"webinar.{webinar.webinar_id}",
            payload={
                "type": "webinar_ended",
                "webinar_id": str(webinar.webinar_id),
            },
        )

        course = lesson.section.course
        publish_event_async.delay(
            routing_key=f"course.{course.course_id}",
            payload={
                "type": "webinar_ended",
                "webinar_id": str(webinar.webinar_id),
                "course_id": str(course.course_id),
                "lesson_id": str(lesson.lesson_id),
                "course_slug": course.slug,
                "lesson_slug": lesson.slug,
            },
        )

        return Response({"detail": "Вебинар завершен"})


@extend_schema_view(
    patch=extend_schema(
        summary="Запланировать или изменить время начала вебинара",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=WebinarScheduleRequestSerializer,
        responses={
            200: WebinarScheduleResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            409: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarScheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_author
    def patch(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        serializer = WebinarScheduleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scheduled_at = serializer.validated_data["scheduled_at"]

        webinar, _ = Webinar.objects.get_or_create(
            lesson=lesson,
            defaults={"started_by": request.user},
        )

        if webinar.status == Webinar.LIVE_STATUS:
            return Response(
                {"detail": "Нельзя изменить расписание вебинара, который сейчас идёт"},
                status=status.HTTP_409_CONFLICT,
            )

        previous_scheduled_at = webinar.scheduled_at
        webinar.scheduled_at = scheduled_at

        update_fields = ["scheduled_at", "updated_at"]
        if webinar.status == Webinar.ENDED_STATUS:
            webinar.status = Webinar.PENDING_STATUS
            webinar.ended_at = None
            update_fields.extend(["status", "ended_at"])

        webinar.save(update_fields=update_fields)

        course = lesson.section.course
        if scheduled_at is None:
            logger.info(
                "Расписание вебинара урока %s снято пользователем %s",
                lesson.slug,
                request.user.pk,
            )
            title = f"Вебинар отменён: {lesson.title}"
            message = (
                f'В курсе "{course.title}" отменено запланированное время '
                f'вебинара урока "{lesson.title}".'
            )
        else:
            logger.info(
                "Расписание вебинара урока %s обновлено пользователем %s на %s",
                lesson.slug,
                request.user.pk,
                scheduled_at.isoformat(),
            )
            scheduled_str = timezone.localtime(scheduled_at).strftime("%d.%m %H:%M")
            if previous_scheduled_at is None:
                title = f"Назначен вебинар: {lesson.title}"
                message = (
                    f'В курсе "{course.title}" назначен вебинар по уроку '
                    f'"{lesson.title}".\nНачало: {scheduled_str}.'
                )
            else:
                title = f"Время вебинара изменено: {lesson.title}"
                message = (
                    f'В курсе "{course.title}" изменено время вебинара по уроку '
                    f'"{lesson.title}".\nНовое начало: {scheduled_str}.'
                )

        if scheduled_at is None:
            from apps.notifications.tasks import send_course_notification

            send_course_notification.delay(course.course_id, title, message)
        else:
            from apps.notifications.tasks import send_webinar_scheduled_notification

            send_webinar_scheduled_notification.delay(
                course_id=str(course.course_id),
                title=title,
                message=message,
                webinar_id=str(webinar.webinar_id),
                course_slug=course.slug,
                lesson_slug=lesson.slug,
                scheduled_at=scheduled_at.isoformat(),
            )

        return Response(
            {
                "webinar_id": str(webinar.webinar_id),
                "scheduled_at": webinar.scheduled_at,
            }
        )


@extend_schema_view(
    get=extend_schema(
        summary="Подключиться к вебинару",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: WebinarTokenSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarJoinView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_enrollment
    def get(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course

        is_teacher = request.user.is_moderator() or (
            request.user.is_teacher() and request.user.is_course_author(course)
        )

        try:
            webinar = Webinar.objects.get(lesson=lesson, status="live")
        except Webinar.DoesNotExist:
            return Response(
                {"detail": "Вебинар не запущен"},
                status=status.HTTP_404_NOT_FOUND,
            )

        uid = user_uid_from_uuid(request.user.pk)
        rtc_role = ROLE_PUBLISHER
        whiteboard_role = "admin" if is_teacher else "writer"
        user_role = "teacher" if is_teacher else "student"

        rtc_token = generate_rtc_token(
            channel_name=webinar.agora_channel_name,
            uid=uid,
            role=rtc_role,
        )

        whiteboard_room_token = generate_whiteboard_room_token(
            room_uuid=webinar.whiteboard_room_uuid,
            role=whiteboard_role,
        )

        rtm_token = generate_rtm_token(uid)
        chat_channel_name = f"chat-{webinar.whiteboard_room_uuid}"

        full_name = f"{request.user.last_name} {request.user.first_name}".strip()
        if not full_name:
            full_name = "Пользователь"

        return Response(
            {
                "webinar_id": str(webinar.webinar_id),
                "rtc_token": rtc_token,
                "rtm_token": rtm_token,
                "agora_app_id": os.getenv("AGORA_APP_ID"),
                "channel_name": webinar.agora_channel_name,
                "chat_channel_name": chat_channel_name,
                "uid": uid,
                "user_name": full_name,
                "whiteboard_app_id": os.getenv("AGORA_WHITEBOARD_APP_ID"),
                "whiteboard_room_uuid": webinar.whiteboard_room_uuid,
                "whiteboard_room_token": whiteboard_room_token,
                "whiteboard_region": os.getenv("AGORA_WHITEBOARD_REGION", "eu"),
                "role": user_role,
                "started_at": webinar.started_at,
            }
        )


@extend_schema_view(
    get=extend_schema(
        summary="Подключение рекордера к вебинару",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses={
            200: WebinarTokenSerializer,
            400: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarRecorderJoinView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, course_slug, lesson_slug):
        token = request.query_params.get("token", "")
        if not token:
            return Response({"detail": "Token required"}, status=status.HTTP_400_BAD_REQUEST)

        webinar_id = verify_recorder_token(token)
        if not webinar_id:
            return Response(
                {"detail": "Invalid or expired token"}, status=status.HTTP_403_FORBIDDEN
            )

        webinar = get_object_or_404(
            Webinar,
            webinar_id=webinar_id,
            lesson__slug=lesson_slug,
            lesson__section__course__slug=course_slug,
            status="live",
        )

        recorder_uid = 999999
        rtc_token = generate_rtc_token(webinar.agora_channel_name, recorder_uid, ROLE_SUBSCRIBER)
        rtm_token = generate_rtm_token(recorder_uid)
        wb_token = generate_whiteboard_room_token(webinar.whiteboard_room_uuid, "reader")
        chat_channel_name = f"chat-{webinar.whiteboard_room_uuid}"

        return Response(
            {
                "webinar_id": str(webinar.webinar_id),
                "rtc_token": rtc_token,
                "rtm_token": rtm_token,
                "agora_app_id": os.getenv("AGORA_APP_ID"),
                "channel_name": webinar.agora_channel_name,
                "chat_channel_name": chat_channel_name,
                "uid": recorder_uid,
                "user_name": "Recorder",
                "whiteboard_app_id": os.getenv("AGORA_WHITEBOARD_APP_ID"),
                "whiteboard_room_uuid": webinar.whiteboard_room_uuid,
                "whiteboard_room_token": wb_token,
                "whiteboard_region": os.getenv("AGORA_WHITEBOARD_REGION", "eu"),
                "role": "recorder",
            }
        )


@extend_schema_view(
    post=extend_schema(
        summary="Начать запись вебинара",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: WebinarRecordingStartResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarRecordingStartView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        webinar = get_object_or_404(Webinar, lesson=lesson, status=Webinar.LIVE_STATUS)

        if webinar.recordings.filter(status=Recording.RECORDING_STATUS).exists():
            return Response({"detail": "Запись уже идет"}, status=status.HTTP_400_BAD_REQUEST)

        recording = Recording.objects.create(
            webinar=webinar,
            started_by=request.user,
            status=Recording.RECORDING_STATUS,
            started_at=timezone.now(),
        )
        recording_uid = "1"
        token = make_recorder_token(str(webinar.webinar_id))
        frontend_base = os.getenv("FRONTEND_BASE_URL", "https://professionkid.ru")
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
        recording.save(update_fields=["resource_id", "sid", "updated_at"])

        from apps.notifications.tasks import publish_event_async

        publish_event_async.delay(
            routing_key=f"webinar.{webinar.webinar_id}",
            payload={
                "type": "recording_started",
                "webinar_id": str(webinar.webinar_id),
                "recording_id": str(recording.recording_id),
                "started_at": recording.started_at.isoformat() if recording.started_at else None,
            },
        )

        return Response({"detail": "Запись началась", "recording_id": str(recording.recording_id)})


@extend_schema_view(
    post=extend_schema(
        summary="Остановить запись вебинара",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: WebinarRecordingStartResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarRecordingStopView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        webinar = get_object_or_404(Webinar, lesson=lesson, status=Webinar.LIVE_STATUS)
        recording = webinar.recordings.filter(status=Recording.RECORDING_STATUS).first()
        if not recording:
            return Response({"detail": "Запись не идет"}, status=status.HTTP_400_BAD_REQUEST)

        _stop_recording(recording)

        return Response(
            {
                "detail": "Запись остановлена",
                "recording_id": str(recording.recording_id),
            }
        )


@extend_schema_view(
    post=extend_schema(
        summary="Сохранить PDF доски записи",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="recording_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: DetailResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
    delete=extend_schema(
        summary="Удалить PDF доски записи",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="recording_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            204: DetailResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class RecordingPdfView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    @require_course_author
    def post(self, request, course_slug, lesson_slug, recording_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        recording = get_object_or_404(
            Recording,
            recording_id=recording_id,
            webinar__lesson=lesson,
            is_deleted=False,
        )

        screenshots = request.FILES.getlist("screenshots")
        if not screenshots:
            return Response(
                {"detail": "Нет скриншотов"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        images = [f.read() for f in screenshots]
        pdf_bytes = img2pdf.convert(images)
        filename = f"recording_{recording.recording_id}.pdf"

        upload_api = build_upload_api()
        binding_api = build_binding_api()
        try:
            asset = upload_api.upload_server_side(
                owner=request.user,
                intent="webinar_whiteboard",
                filename=filename,
                mime_type="application/pdf",
                body=pdf_bytes,
            )
            binding_api.sync_single(
                content_object=recording,
                role="whiteboard_pdf",
                asset_id=asset.asset_id,
                owner=None,
            )
        except AssetError as exc:
            return process_error_response(exc)

        if recording.whiteboard_pdf_url:
            recording.whiteboard_pdf_url = ""
            recording.save(update_fields=["whiteboard_pdf_url", "updated_at"])

        invalidate_lesson_detail_cache(course_slug, lesson_slug)

        return Response({"detail": "pdf доски сохранен"})

    @require_course_author
    def delete(self, request, course_slug, lesson_slug, recording_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        recording = get_object_or_404(
            Recording,
            recording_id=recording_id,
            webinar__lesson=lesson,
            is_deleted=False,
        )

        binding_api = build_binding_api()
        try:
            binding_api.sync_single(
                content_object=recording,
                role="whiteboard_pdf",
                asset_id=None,
                owner=None,
            )
        except AssetError as exc:
            return process_error_response(exc)

        if recording.whiteboard_pdf_url:
            recording.whiteboard_pdf_url = ""
            recording.save(update_fields=["whiteboard_pdf_url", "updated_at"])

        invalidate_lesson_detail_cache(course_slug, lesson_slug)

        return Response({"detail": "pdf доски удален"}, status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(
        summary="Сохранить финальный PDF доски при завершении вебинара",
        description=(
            "Создает служебную Recording (status=ready, без видео) "
            "с PDF доски, отражающим ее состояние на момент завершения вебинара. "
            "Вызывается фронтом ПЕРЕД POST /webinar/stop/."
        ),
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: DetailResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class WebinarFinalPdfView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )

        webinar = get_object_or_404(Webinar, lesson=lesson)

        screenshots = request.FILES.getlist("screenshots")
        if not screenshots:
            return Response(
                {"detail": "Нет скриншотов"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            images = [f.read() for f in screenshots]
            pdf_bytes = img2pdf.convert(images)
        except Exception:
            logger.exception(
                "Ошибка конвертации финальных скриншотов в PDF для вебинара %s",
                webinar.webinar_id,
            )
            return Response(
                {"detail": "Не удалось обработать скриншоты"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        now = timezone.now()
        recording = Recording.objects.create(
            webinar=webinar,
            started_by=request.user,
            status=Recording.READY_STATUS,
            started_at=now,
            ended_at=now,
        )

        filename = f"whiteboard_{recording.recording_id}.pdf"
        upload_api = build_upload_api()
        binding_api = build_binding_api()
        try:
            asset = upload_api.upload_server_side(
                owner=request.user,
                intent="webinar_whiteboard",
                filename=filename,
                mime_type="application/pdf",
                body=pdf_bytes,
            )
            binding_api.sync_single(
                content_object=recording,
                role="whiteboard_pdf",
                asset_id=asset.asset_id,
                owner=None,
            )
        except AssetError as exc:
            recording.delete()
            return process_error_response(exc)

        logger.info(
            "Финальный PDF доски сохранен для вебинара %s, recording %s",
            webinar.webinar_id,
            recording.recording_id,
        )

        return Response(
            {
                "detail": "Финальный PDF доски сохранен",
                "recording_id": str(recording.recording_id),
            }
        )


@extend_schema_view(
    delete=extend_schema(
        summary="Удалить запись вебинара",
        tags=["Webinar"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="recording_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            204: DetailResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class RecordingDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    @require_course_author
    def delete(self, request, course_slug, lesson_slug, recording_id):
        lesson = get_object_or_404(
            Lesson.objects.select_related("section__course"),
            slug=lesson_slug,
            section__course__slug=course_slug,
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
        recording.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

        return Response({"detail": "запись удалена"}, status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(
        summary="DRM-авторизация Kinescope",
        tags=["Webinar"],
        responses={
            200: None,
            403: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class KinescopeDRMAuthView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request):
        import jwt
        from django.conf import settings as django_settings

        from apps.users.models import User

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        expected_user = os.getenv("KINESCOPE_DRM_AUTH_USERNAME", "")
        expected_pass = os.getenv("KINESCOPE_DRM_AUTH_PASSWORD", "")

        if not self._verify_basic_auth(auth_header, expected_user, expected_pass):
            return Response(status=status.HTTP_403_FORBIDDEN)

        video_id = request.data.get("id", "")
        drm_token = request.data.get("token", "")

        if not video_id or not drm_token:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            payload = jwt.decode(
                drm_token,
                django_settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            user_id = payload.get("user_id")
            token_video_id = payload.get("video_id")
        except Exception:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if token_video_id != video_id:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            recording = Recording.objects.select_related("webinar__lesson__section__course").get(
                kinescope_video_id=video_id, is_deleted=False
            )
        except Recording.DoesNotExist:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            user = User.objects.get(pk=user_id)
            course = recording.webinar.lesson.section.course
            if user.is_enrolled(course) or course.authors.filter(pk=user.pk).exists():
                return Response(status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_403_FORBIDDEN)

    @staticmethod
    def _verify_basic_auth(auth_header, expected_user, expected_pass):
        import base64 as b64

        if not auth_header.startswith("Basic "):
            return False
        try:
            decoded = b64.b64decode(auth_header[6:]).decode()
            username, password = decoded.split(":", 1)
            return username == expected_user and password == expected_pass
        except Exception:
            return False
