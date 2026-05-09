from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.api.permissions import require_course_author
from apps.courses.models import Course, CourseEnrollment

from ..models import CourseApplication
from .serializers import ApplicationReviewedSerializer, CourseApplicationSerializer

SCHEMA_DETAIL = {"type": "object", "properties": {"detail": {"type": "string"}}}


class CourseApplicationListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Список заявок на курс",
        tags=["Applications"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=["pending", "approved", "rejected"],
            ),
        ],
        responses={
            200: CourseApplicationSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def get(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        qs = CourseApplication.objects.filter(course=course).select_related("user", "reviewed_by")

        status_filter = request.query_params.get("status")
        if status_filter in (
            CourseApplication.PENDING,
            CourseApplication.APPROVED,
            CourseApplication.REJECTED,
        ):
            qs = qs.filter(status=status_filter)

        serializer = CourseApplicationSerializer(qs, many=True)
        return Response(serializer.data)


class CourseApplyView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Подать заявку на курс",
        tags=["Applications"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            201: None,
            400: {"schema": SCHEMA_DETAIL},
            401: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            409: {"schema": SCHEMA_DETAIL},
        },
    )
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)

        if not course.is_special:
            return Response(
                {"detail": "На этот курс нельзя подать заявку"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.is_enrolled(course):
            return Response(
                {"detail": "Вы уже записаны на этот курс"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if CourseApplication.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "Заявка уже подана"},
                status=status.HTTP_409_CONFLICT,
            )

        CourseApplication.objects.create(user=request.user, course=course)
        return Response(status=status.HTTP_201_CREATED)


class CourseWithdrawApplicationView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Отозвать заявку на курс",
        tags=["Applications"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            409: {"schema": SCHEMA_DETAIL},
        },
    )
    def delete(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        application = CourseApplication.objects.filter(user=request.user, course=course).first()

        if application is None:
            return Response(
                {"detail": "Заявка не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if application.status != CourseApplication.PENDING:
            return Response(
                {"detail": "Нельзя отозвать рассмотренную заявку"},
                status=status.HTTP_409_CONFLICT,
            )

        application.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseApplicationApproveView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Одобрить заявку",
        tags=["Applications"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="application_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: ApplicationReviewedSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            409: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug, application_id):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        application = get_object_or_404(
            CourseApplication, application_id=application_id, course=course
        )

        if application.status != CourseApplication.PENDING:
            return Response(
                {"detail": "Заявка уже рассмотрена"},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            application.status = CourseApplication.APPROVED
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

            CourseEnrollment.objects.get_or_create(
                user=application.user,
                course=course,
                defaults={
                    "source": CourseEnrollment.SOURCE_APPLICATION,
                    "payment": None,
                    "access_expires_at": timezone.now() + timedelta(days=365),
                },
            )

        from apps.notifications.dispatcher import dispatcher
        from apps.notifications.events import ApplicationStatusChangedEvent

        dispatcher.dispatch(
            ApplicationStatusChangedEvent(
                user_id=application.user.id,
                course_title=course.title,
                new_status=CourseApplication.APPROVED,
            )
        )

        return Response(ApplicationReviewedSerializer(application).data)


class CourseApplicationRejectView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Отклонить заявку",
        tags=["Applications"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="application_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: ApplicationReviewedSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            409: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug, application_id):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        application = get_object_or_404(
            CourseApplication, application_id=application_id, course=course
        )

        if application.status != CourseApplication.PENDING:
            return Response(
                {"detail": "Заявка уже рассмотрена"},
                status=status.HTTP_409_CONFLICT,
            )

        application.status = CourseApplication.REJECTED
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        from apps.notifications.dispatcher import dispatcher
        from apps.notifications.events import ApplicationStatusChangedEvent

        dispatcher.dispatch(
            ApplicationStatusChangedEvent(
                user_id=application.user.id,
                course_title=course.title,
                new_status=CourseApplication.REJECTED,
            )
        )

        return Response(ApplicationReviewedSerializer(application).data)
