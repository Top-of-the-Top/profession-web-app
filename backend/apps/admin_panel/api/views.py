from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_panel.models import Invitation
from apps.core.api.permissions import require_moderator
from apps.core.api.serializers import ServiceErrorResponseSerializer
from apps.core.processors.error_processor import process_error_response
from apps.courses.api.utils.cache_utils import invalidate_on_course_model_change
from apps.courses.models import Course
from apps.users.api.utils.crypto_utils import encrypt_data
from apps.users.api.utils.notification_utils import send_teacher_invite_email
from apps.users.api.utils.token_utils import get_tokens_for_user
from apps.users.models import Profile, User

from .errors import (
    AuthorAlreadyOnCourse,
    AuthorNotOnCourse,
    CourseAlreadyDraft,
    CourseAlreadyPublished,
    InvitationAlreadyUsed,
    InvitationExpired,
    InvitationNotFound,
    InvitationSendFailed,
    UserNotTeacher,
)
from .serializers import InvitationCreateSerializer, InvitationSerializer, TeacherSerializer

SCHEMA_DETAIL = {"type": "object", "properties": {"detail": {"type": "string"}}}
SCHEMA_VALIDATION = {"type": "object", "description": "Объект с ошибками валидации по полям."}

_PATH_COURSE = OpenApiParameter(
    "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
)


class TeacherListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Список преподавателей",
        description="Возвращает всех пользователей с ролью teacher. Доступно только модератору.",
        tags=["Admin Panel"],
        responses={
            200: TeacherSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def get(self, request):  # noqa: ARG002
        teachers = User.objects.filter(role=User.ROLE_TEACHER)
        return Response(TeacherSerializer(teachers, many=True).data)


class CourseAddAuthorView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Добавить преподавателя на курс",
        description=(
            "Назначает преподавателя автором курса. "
            "Query-параметр user_id обязателен. Доступно только модератору."
        ),
        tags=["Admin Panel"],
        parameters=[
            _PATH_COURSE,
            OpenApiParameter(
                "user_id",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                required=True,
                description="ID пользователя с ролью teacher",
            ),
        ],
        request=None,
        responses={
            200: TeacherSerializer(many=True),
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"detail": "Параметр user_id обязателен."}, status=status.HTTP_400_BAD_REQUEST
            )
        user = get_object_or_404(User, pk=user_id)
        if not user.is_teacher():
            return process_error_response(UserNotTeacher())
        if course.authors.filter(pk=user.pk).exists():
            return process_error_response(AuthorAlreadyOnCourse())
        course.authors.add(user)
        invalidate_on_course_model_change(course.slug)
        return Response(TeacherSerializer(course.authors.all(), many=True).data)


class CourseRemoveAuthorView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Снять преподавателя с курса",
        description=(
            "Убирает преподавателя из авторов курса. "
            "Query-параметр user_id обязателен. Доступно только модератору."
        ),
        tags=["Admin Panel"],
        parameters=[
            _PATH_COURSE,
            OpenApiParameter(
                "user_id",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
                required=True,
                description="ID пользователя",
            ),
        ],
        request=None,
        responses={
            200: TeacherSerializer(many=True),
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"detail": "Параметр user_id обязателен."}, status=status.HTTP_400_BAD_REQUEST
            )
        user = get_object_or_404(User, pk=user_id)
        if not course.authors.filter(pk=user.pk).exists():
            return process_error_response(AuthorNotOnCourse())
        course.authors.remove(user)
        invalidate_on_course_model_change(course.slug)
        return Response(TeacherSerializer(course.authors.all(), many=True).data)


class CoursePublishView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Опубликовать курс",
        description="Переводит курс в статус published. Доступно только модератору.",
        tags=["Admin Panel"],
        parameters=[_PATH_COURSE],
        request=None,
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}}},
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        if course.type == Course.PUBLISHED_STATUS:
            return process_error_response(CourseAlreadyPublished())
        course.type = Course.PUBLISHED_STATUS
        course.last_modified_by = request.user
        course.save(update_fields=["type", "last_modified_by", "updated_at"])
        return Response({"status": course.type})


class CourseUnpublishView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Снять курс с публикации",
        description="Переводит курс обратно в статус draft. Доступно только модератору.",
        tags=["Admin Panel"],
        parameters=[_PATH_COURSE],
        request=None,
        responses={
            200: {"type": "object", "properties": {"status": {"type": "string"}}},
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        if course.type == Course.DRAFT_STATUS:
            return process_error_response(CourseAlreadyDraft())
        course.type = Course.DRAFT_STATUS
        course.last_modified_by = request.user
        course.save(update_fields=["type", "last_modified_by", "updated_at"])
        return Response({"status": course.type})


class InvitationListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Список приглашений",
        description="Возвращает все активные и использованные приглашения. Доступно только модератору.",
        tags=["Admin Panel"],
        responses={
            200: InvitationSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def get(self, request):  # noqa: ARG002
        invites = Invitation.objects.select_related("invited_by").all()
        return Response(InvitationSerializer(invites, many=True).data)


class InviteTeacherview(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Пригласить преподавателя",
        description=(
            "Создаёт инвайт-ссылку и отправляет письмо на указанный email. "
            "Если письмо не доставлено — инвайт удаляется. Доступно только модератору."
        ),
        tags=["Admin Panel"],
        request=InvitationCreateSerializer,
        responses={
            201: InvitationSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            500: ServiceErrorResponseSerializer,
        },
    )
    @require_moderator
    def post(self, request):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite = Invitation.objects.create(
            email=serializer.validated_data["email"],
            invited_by=request.user,
        )

        from django.conf import settings

        invite_url = f"{settings.FRONTEND_HOST}/register?invite={invite.token}"
        ok, _ = send_teacher_invite_email(invite.email, invite_url)
        if not ok:
            invite.delete()
            return process_error_response(InvitationSendFailed())

        return Response(InvitationSerializer(invite).data, status=status.HTTP_201_CREATED)


class InviteValidateView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Проверить инвайт-токен",
        description=(
            "Проверяет валидность токена из ссылки-приглашения. "
            "Возвращает email, на который выдан инвайт."
        ),
        tags=["Admin Panel"],
        parameters=[
            OpenApiParameter(
                "token",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=True,
                description="Токен из ссылки-приглашения",
            ),
        ],
        responses={
            200: {"type": "object", "properties": {"email": {"type": "string"}}},
            400: ServiceErrorResponseSerializer,
            404: ServiceErrorResponseSerializer,
        },
    )
    def get(self, request):
        token = request.query_params.get("token", "").strip()
        invite = Invitation.objects.filter(token=token).first()
        if not invite:
            return process_error_response(InvitationNotFound())
        if invite.is_used:
            return process_error_response(InvitationAlreadyUsed())
        if invite.is_expired:
            return process_error_response(InvitationExpired())
        return Response({"email": invite.email})


class RegisterByInviteView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Регистрация преподавателя по приглашению",
        description=(
            "Создаёт аккаунт преподавателя по одноразовому инвайт-токену. "
            "После успешной регистрации возвращаются JWT-токены."
        ),
        tags=["Admin Panel"],
        request={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Токен из ссылки-приглашения"},
                "password": {"type": "string", "description": "Пароль (минимум 8 символов)"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
            },
            "required": ["token", "password", "first_name", "last_name"],
        },
        responses={
            201: {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "refresh_token": {"type": "string"},
                    "role": {"type": "string"},
                },
            },
            400: ServiceErrorResponseSerializer,
            404: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        token = (request.data.get("token") or "").strip()
        password = (request.data.get("password") or "").strip()
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()

        if not all([token, password, first_name, last_name]):
            return Response(
                {"detail": "Все поля обязательны."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) < 8:
            return Response(
                {"password": ["Минимум 8 символов."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invite = Invitation.objects.filter(token=token).first()
        if not invite:
            return process_error_response(InvitationNotFound())
        if invite.is_used:
            return process_error_response(InvitationAlreadyUsed())
        if invite.is_expired:
            return process_error_response(InvitationExpired())

        email_cipher = encrypt_data(invite.email)
        user = User.objects.create_user(
            email_cipher=email_cipher,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=User.ROLE_TEACHER,
        )
        Profile.objects.create(user=user)

        invite.used_at = timezone.now()
        invite.save(update_fields=["used_at"])

        return Response(get_tokens_for_user(user), status=status.HTTP_201_CREATED)
