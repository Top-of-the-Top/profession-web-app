from django.core.cache import caches
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.serializers import ServiceErrorResponseSerializer
from apps.core.processors.error_processor import process_error_response
from apps.courses.api.permissions import require_course_author, require_course_enrollment
from apps.courses.api.schema import SCHEMA_DETAIL, SCHEMA_VALIDATION
from apps.courses.api.utils.cache_utils import (
    attempt_detail_cache_key,
    attempt_draft_cache_key,
    attempt_list_by_course_cache_key,
    attempt_list_cache_key,
    invalidate_attempt_cache,
)
from apps.courses.models import Homework, Lesson
from apps.homeworks.models import Attempt

from ..services.attempt_service import AttemptService
from ..services.errors import HomeworkServiceError, RequestValidationError
from ..services.review_service import ReviewService, TaskReviewItem
from .serializers import (
    AttemptReviewSerializer,
    AttemptSerializer,
    AttemptSubmitSerializer,
    MyAttemptSerializer,
    StudentAttemptSerializer,
)

HOMEWORK_SLUG_PARAM = OpenApiParameter(
    name="homework_slug",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.PATH,
    required=True,
    description="Slug домашнего задания",
)

COURSE_SLUG_PARAM = OpenApiParameter(
    name="course_slug",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.PATH,
    required=True,
    description="Slug курса",
)

ATTEMPT_ID_PARAM = OpenApiParameter(
    name="attempt_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    required=True,
    description="UUID попытки",
)


class HomeworkAttemptView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Текущая попытка по домашнему заданию",
        description=(
            "Возвращает черновик попытки студента. "
            "Если попытки ещё нет — создаёт её автоматически. "
            "Требует записи на курс."
        ),
        tags=["Homework"],
        parameters=[COURSE_SLUG_PARAM, HOMEWORK_SLUG_PARAM],
        responses={
            200: AttemptSerializer,
            400: ServiceErrorResponseSerializer,
            401: ServiceErrorResponseSerializer,
            403: ServiceErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ServiceErrorResponseSerializer,
        },
    )
    @require_course_enrollment
    def get(self, request, course_slug, homework_slug):
        cache = caches["default"]
        cache_key = attempt_draft_cache_key(request.user.id, homework_slug)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        homework = get_object_or_404(
            Homework,
            slug=homework_slug,
            lesson__section__course__slug=course_slug,
        )
        service = AttemptService()
        try:
            attempt = service.get_or_create_draft(user=request.user, homework=homework)
        except HomeworkServiceError as exc:
            return process_error_response(exc)

        data = AttemptSerializer(attempt, context={"request": request}).data
        cache.set(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)


def _build_my_attempts(user, homework_filter):
    hw_filter = {
        k.replace("homework__", "", 1) if k.startswith("homework__") else k: v
        for k, v in homework_filter.items()
    }

    homeworks = (
        Homework.objects.filter(**hw_filter, type=Homework.PUBLISHED_STATUS)
        .select_related("lesson__section__course")
        .prefetch_related("attempt_set")
        .order_by(
            "lesson__section__section_number",
            "lesson__lesson_number",
            "homework_number",
        )
    )

    attempt_by_hw = {
        a.homework_id: a for a in Attempt.objects.filter(homework__in=homeworks, user=user)
    }

    items = []
    for hw in homeworks:
        attempt = attempt_by_hw.get(hw.homework_id)
        items.append(
            {
                "attempt_id": str(attempt.attempt_id) if attempt else None,
                "status": attempt.status if attempt else "to_do",
                "homework_id": str(hw.homework_id),
                "homework_slug": hw.slug,
                "homework_title": hw.title,
                "deadline": hw.deadline,
                "course_slug": hw.lesson.section.course.slug,
                "course_title": hw.lesson.section.course.title,
                "lesson_slug": hw.lesson.slug,
                "lesson_title": hw.lesson.title,
                "grade": attempt.grade if attempt else None,
                "max_points": hw.max_points,
                "send_at": attempt.send_at if attempt else None,
            }
        )
    return items


class StudentAttemptsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Домашние задания и попытки",
        description=(
            "Для студента — список его попыток по купленным курсам. "
            "Для преподавателя — попытки студентов по своим курсам. "
            "Для модератора — все попытки на платформе. "
            "Можно сузить выборку параметрами course_slug и lesson_slug."
        ),
        tags=["Home"],
        parameters=[
            OpenApiParameter(
                "course_slug",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                description="Фильтр по slug курса",
            ),
            OpenApiParameter(
                "lesson_slug",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                description="Фильтр по slug урока (требует course_slug)",
            ),
        ],
        responses={
            200: MyAttemptSerializer(many=True),
            400: ServiceErrorResponseSerializer,
            401: SCHEMA_DETAIL,
            403: ServiceErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ServiceErrorResponseSerializer,
        },
    )
    def get(self, request):
        from apps.courses.models import Course

        course_slug = request.query_params.get("course_slug")
        lesson_slug = request.query_params.get("lesson_slug")

        user = request.user
        cache = caches["default"]

        attempt_filter = {}
        teacher_course = None

        if lesson_slug and course_slug:
            lesson = get_object_or_404(
                Lesson.objects.select_related("section__course"),
                slug=lesson_slug,
                section__course__slug=course_slug,
            )
            attempt_filter = {"homework__lesson": lesson}
            teacher_course = lesson.section.course
            list_cache_key = attempt_list_cache_key(lesson_slug)
            list_cache_key_user = attempt_list_cache_key(lesson_slug, user.id)
        elif course_slug:
            course = get_object_or_404(Course, slug=course_slug)
            attempt_filter = {"homework__lesson__section__course": course}
            teacher_course = course
            list_cache_key = attempt_list_by_course_cache_key(course_slug)
            list_cache_key_user = attempt_list_by_course_cache_key(course_slug, user.id)
        else:
            if user.is_student():
                purchased_ids = user.get_purchased_courses_ids()
                attempt_filter = {"homework__lesson__section__course_id__in": purchased_ids}
            list_cache_key = "default:attempt:list:all"
            list_cache_key_user = f"default:attempt:list:all:{int(user.id)}"

        if user.is_moderator():
            cached = cache.get(list_cache_key)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)
            attempts = (
                Attempt.objects.filter(**attempt_filter)
                .select_related(
                    "homework__lesson__section__course",
                    "user",
                )
                .order_by("-created_at")
            )
            data = {
                "student_attempts": {"items": StudentAttemptSerializer(attempts, many=True).data}
            }
            cache.set(list_cache_key, data)
            return Response(data, status=status.HTTP_200_OK)

        if user.is_teacher():
            if teacher_course is not None and not user.is_course_author(teacher_course):
                return Response(
                    {"detail": "Вы не являетесь автором этого курса"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            cached = cache.get(list_cache_key)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)
            authored_ids = list(
                Course.objects.filter(authors=user).values_list("course_id", flat=True)
            )
            teacher_filter = {
                **attempt_filter,
                "homework__lesson__section__course_id__in": authored_ids,
            }
            attempts = (
                Attempt.objects.filter(**teacher_filter)
                .select_related(
                    "homework__lesson__section__course",
                    "user",
                )
                .order_by("-created_at")
            )
            data = {
                "student_attempts": {"items": StudentAttemptSerializer(attempts, many=True).data}
            }
            cache.set(list_cache_key, data)
            return Response(data, status=status.HTTP_200_OK)

        cached = cache.get(list_cache_key_user)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        data = {"my_attempts": {"items": _build_my_attempts(user, attempt_filter)}}
        cache.set(list_cache_key_user, data)
        return Response(data, status=status.HTTP_200_OK)


class AttemptDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Попытка студента",
        description=(
            "Возвращает попытку с ответами на все вопросы и задания. "
            "Вопросы (type=question) содержат результат автопроверки. "
            "Задания (type=task) содержат поле review — оценку преподавателя или null, "
            "если задание ещё не проверено. "
            "Доступно автору курса и модератору."
        ),
        tags=["Homework"],
        parameters=[COURSE_SLUG_PARAM, ATTEMPT_ID_PARAM],
        responses={
            200: AttemptSerializer,
            400: ServiceErrorResponseSerializer,
            401: ServiceErrorResponseSerializer,
            403: ServiceErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            500: ServiceErrorResponseSerializer,
        },
    )
    @require_course_author
    def get(self, request, course_slug, attempt_id):
        cache = caches["default"]
        cache_key = attempt_detail_cache_key(attempt_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        attempt = get_object_or_404(
            Attempt.objects.select_related("homework").prefetch_related(
                "question_answers__question",
                "task_answers__task",
                "task_answers__review__reviewer__profile",
            ),
            attempt_id=attempt_id,
            homework__lesson__section__course__slug=course_slug,
        )
        data = AttemptSerializer(attempt, context={"request": request}).data
        cache.set(cache_key, data)
        return Response(data, status=status.HTTP_200_OK)


class AttemptReviewView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Проверить попытку (преподаватель)",
        description=(
            "Выставляет баллы и комментарий по каждому заданию (Task). "
            "Попытка должна быть в статусе submitted. "
            "Повторный вызов обновляет ранее выставленную оценку. "
            "Поле reviewer в ответе равно null только если аккаунт проверяющего удалён."
        ),
        tags=["Homework"],
        parameters=[COURSE_SLUG_PARAM, ATTEMPT_ID_PARAM],
        request=AttemptReviewSerializer,
        responses={
            200: AttemptSerializer,
            400: ServiceErrorResponseSerializer,
            401: ServiceErrorResponseSerializer,
            403: ServiceErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            409: ServiceErrorResponseSerializer,
            500: ServiceErrorResponseSerializer,
        },
    )
    @require_course_author
    def post(self, request, course_slug, attempt_id):
        attempt = get_object_or_404(
            Attempt.objects.select_related("homework__lesson__section__course"),
            attempt_id=attempt_id,
            homework__lesson__section__course__slug=course_slug,
        )

        serializer = AttemptReviewSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except DRFValidationError as exc:
            return process_error_response(RequestValidationError(exc.detail))
        payload = serializer.validated_data

        if str(attempt.attempt_id) != str(payload["attempt_id"]):
            return process_error_response(
                RequestValidationError("attempt_id в теле не совпадает с URL.")
            )

        items = [
            TaskReviewItem(
                task_answer_id=str(item["task_answer_id"]),
                points=item["points"],
                comment=item.get("comment"),
            )
            for item in payload["items"]
        ]

        service = ReviewService()
        try:
            attempt = service.review_attempt(
                attempt=attempt,
                reviewer=request.user,
                items=items,
            )
        except HomeworkServiceError as exc:
            return process_error_response(exc)

        invalidate_attempt_cache(
            user_id=attempt.user_id,
            homework_slug=attempt.homework.slug,
            attempt_id=attempt.attempt_id,
            lesson_slug=attempt.homework.lesson.slug,
            course_slug=attempt.homework.lesson.section.course.slug,
        )
        return Response(
            AttemptSerializer(attempt, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class HomeworkAttemptSubmitView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Сдать домашнее задание на проверку",
        description=(
            "Сохраняет ответы студента и переводит попытку в статус submitted. "
            "Автоматически запускает проверку вопросов с вариантами ответа. "
            "Требует записи на курс."
        ),
        tags=["Homework"],
        parameters=[COURSE_SLUG_PARAM, HOMEWORK_SLUG_PARAM],
        request=AttemptSubmitSerializer,
        responses={
            201: AttemptSerializer,
            400: SCHEMA_VALIDATION,
            401: ServiceErrorResponseSerializer,
            403: ServiceErrorResponseSerializer,
            404: SCHEMA_DETAIL,
            409: ServiceErrorResponseSerializer,
            413: ServiceErrorResponseSerializer,
            500: ServiceErrorResponseSerializer,
            503: ServiceErrorResponseSerializer,
        },
    )
    @require_course_enrollment
    def post(self, request, course_slug, homework_slug):
        homework = get_object_or_404(
            Homework,
            slug=homework_slug,
            lesson__section__course__slug=course_slug,
        )
        serializer = AttemptSubmitSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except DRFValidationError as exc:
            return process_error_response(RequestValidationError(exc.detail))
        payload = serializer.validated_data

        service = AttemptService()
        try:
            attempt = service.get_or_create_draft(user=request.user, homework=homework)
        except HomeworkServiceError as exc:
            return process_error_response(exc)

        try:
            attempt = service.submit(
                attempt=attempt,
                payload_attempt_id=payload["attempt_id"],
                send_at=payload["send_at"],
                items=payload["items"],
            )
        except HomeworkServiceError as exc:
            return process_error_response(exc)

        invalidate_attempt_cache(
            user_id=request.user.id,
            homework_slug=homework_slug,
            attempt_id=attempt.attempt_id,
            lesson_slug=attempt.homework.lesson.slug,
            course_slug=attempt.homework.lesson.section.course.slug,
        )
        return Response(
            AttemptSerializer(attempt, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
