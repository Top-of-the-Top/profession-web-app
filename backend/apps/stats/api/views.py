import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stats.api.permissions import (
    IsEnrolledOrCourseStaff,
    IsTeacherAuthorOrModerator,
)
from apps.stats.api.serializers import (
    RecordingViewHeartbeatRequestSerializer,
    RecordingViewHeartbeatResponseSerializer,
    SchoolCourseRowSerializer,
    SchoolTeacherRowSerializer,
    StudentCardSerializer,
    StudentRowSerializer,
    WebinarAttendanceHeartbeatResponseSerializer,
    WebinarTableRowSerializer,
)
from apps.stats.services.dashboard_service import (
    list_students,
    list_webinars_table,
    school_courses_table,
    school_teachers_table,
    student_card,
)
from apps.stats.services.progress_service import (
    RecordingViewService,
    WebinarAttendanceService,
)
from apps.webinars.models import Recording, Webinar

logger = logging.getLogger(__name__)


class WebinarHeartbeatView(APIView):
    permission_classes = (IsAuthenticated, IsEnrolledOrCourseStaff)

    @extend_schema(
        summary="Heartbeat присутствия на вебинаре",
        tags=["Statistics"],
        parameters=[
            OpenApiParameter(name="webinar_id", type=OpenApiTypes.UUID, location=OpenApiParameter.PATH),
        ],
        request=None,
        responses={200: WebinarAttendanceHeartbeatResponseSerializer},
    )
    def post(self, request, webinar_id):
        webinar = get_object_or_404(Webinar, pk=webinar_id)
        self.check_object_permissions(request, webinar)

        attendance, total = WebinarAttendanceService.heartbeat(
            user=request.user, webinar=webinar
        )
        logger.info(
            "Heartbeat вебинара: user=%s webinar=%s total=%ss",
            request.user.pk, webinar.pk, total,
        )
        return Response(
            {
                "attendance_id": str(attendance.attendance_id),
                "watched_seconds_total": total,
            },
            status=status.HTTP_200_OK,
        )


class RecordingHeartbeatView(APIView):
    permission_classes = (IsAuthenticated, IsEnrolledOrCourseStaff)

    @extend_schema(
        summary="Heartbeat просмотра записи",
        tags=["Statistics"],
        parameters=[
            OpenApiParameter(name="recording_id", type=OpenApiTypes.UUID, location=OpenApiParameter.PATH),
        ],
        request=RecordingViewHeartbeatRequestSerializer,
        responses={200: RecordingViewHeartbeatResponseSerializer},
    )
    def post(self, request, recording_id):
        recording = get_object_or_404(Recording, pk=recording_id, is_deleted=False)
        self.check_object_permissions(request, recording)

        ser = RecordingViewHeartbeatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        view = RecordingViewService.heartbeat(
            user=request.user,
            recording=recording,
            current_position=ser.validated_data["current_position"],
        )
        logger.info(
            "Heartbeat записи: user=%s recording=%s position=%ss watched=%ss",
            request.user.pk, recording.pk, view.last_position, view.watched_seconds,
        )
        return Response(
            {
                "view_id": str(view.view_id),
                "watched_seconds": view.watched_seconds,
                "last_position": view.last_position,
            },
            status=status.HTTP_200_OK,
        )


class StatsWebinarsView(APIView):
    permission_classes = (IsAuthenticated, IsTeacherAuthorOrModerator)

    @extend_schema(
        summary="Таблица вебинаров",
        tags=["Statistics"],
        parameters=[
            OpenApiParameter(
                name="course_title", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                required=False, description="Фильтр по названию курса (частичное совпадение)",
            ),
            OpenApiParameter(
                name="from", type=OpenApiTypes.DATETIME, location=OpenApiParameter.QUERY,
                required=False, description="Нижняя граница периода (по ended_at)",
            ),
            OpenApiParameter(
                name="to", type=OpenApiTypes.DATETIME, location=OpenApiParameter.QUERY,
                required=False, description="Верхняя граница периода (по ended_at)",
            ),
        ],
        responses={200: WebinarTableRowSerializer(many=True)},
    )
    def get(self, request):
        rows = list_webinars_table(
            requester=request.user,
            course_title=request.query_params.get("course_title"),
            date_from=request.query_params.get("from") or None,
            date_to=request.query_params.get("to") or None,
        )
        return Response(WebinarTableRowSerializer(rows, many=True).data)


class StatsStudentsView(APIView):
    permission_classes = (IsAuthenticated, IsTeacherAuthorOrModerator)

    @extend_schema(
        summary="Список учеников",
        tags=["Statistics"],
        parameters=[
            OpenApiParameter(
                name="course_title", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                required=False, description="Фильтр по названию курса (частичное совпадение)",
            ),
            OpenApiParameter(
                name="q", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                required=False, description="Поиск по ФИО / email / телефону",
            ),
        ],
        responses={200: StudentRowSerializer(many=True)},
    )
    def get(self, request):
        rows = list_students(
            requester=request.user,
            course_title=request.query_params.get("course_title"),
            query=request.query_params.get("q"),
        )
        return Response(StudentRowSerializer(rows, many=True).data)


class StatsStudentCardView(APIView):
    permission_classes = (IsAuthenticated, IsTeacherAuthorOrModerator)

    @extend_schema(
        summary="Карточка ученика по курсу",
        tags=["Statistics"],
        parameters=[
            OpenApiParameter(name="user_id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH),
            OpenApiParameter(name="course_id", type=OpenApiTypes.UUID, location=OpenApiParameter.PATH),
        ],
        responses={200: StudentCardSerializer},
    )
    def get(self, request, user_id, course_id):
        from apps.courses.models import Course

        course = get_object_or_404(Course, pk=course_id)
        data = student_card(
            requester=request.user,
            student_id=user_id,
            course_slug=course.slug,
        )
        if data is None:
            return Response(
                {"detail": "Нет доступа к карточке ученика"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(StudentCardSerializer(data).data)


class StatsSchoolCoursesView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Сравнение курсов (модератор)",
        tags=["Statistics"],
        responses={200: SchoolCourseRowSerializer(many=True)},
    )
    def get(self, request):
        if not request.user.is_moderator():
            return Response(
                {"detail": "Доступно только модератору"},
                status=status.HTTP_403_FORBIDDEN,
            )
        rows = school_courses_table()
        return Response(SchoolCourseRowSerializer(rows, many=True).data)


class StatsSchoolTeachersView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Активность преподавателей (модератор)",
        tags=["Statistics"],
        responses={200: SchoolTeacherRowSerializer(many=True)},
    )
    def get(self, request):
        if not request.user.is_moderator():
            return Response(
                {"detail": "Доступно только модератору"},
                status=status.HTTP_403_FORBIDDEN,
            )
        rows = school_teachers_table()
        return Response(SchoolTeacherRowSerializer(rows, many=True).data)
