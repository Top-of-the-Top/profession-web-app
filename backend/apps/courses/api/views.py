import logging

from django.core.cache import caches
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.permissions import require_moderator
from apps.core.api.serializers import ServiceErrorResponseSerializer
from apps.core.processors.error_processor import process_error_response
from apps.webinars.models import Webinar

from ..models import Course, Homework, Question, Section, Task
from .errors import CourseNotPublished, NotEnrolled, ScheduleDateInvalid
from .permissions import (
    course_content_visibility,
    get_courses_for_user,
    published_lesson_hierarchy_q,
    require_course_author,
    require_course_enrollment,
)
from .schema import SCHEMA_DETAIL, SCHEMA_VALIDATION
from .serializers import (
    CourseDTOSerializer,
    CourseHomeSerializer,
    CourseListResponseSerializer,
    CourseSerializer,
    CourseStoreDTOSerializer,
    HomeworkDetailSerializer,
    HomeworkSerializer,
    LessonCreateSerializer,
    LessonDetailReadSerializer,
    LessonSerializer,
    LessonSimpleCreateSerializer,
    MyContentCourseSerializer,
    QuestionSerializer,
    ScheduleItemSerializer,
    ScheduleResponseSerializer,
    SectionSerializer,
    TaskSerializer,
)
from .utils.cache_utils import (
    cached_detail_response,
    course_detail_cache_key,
    course_list_cache_key,
    homework_detail_cache_key,
    landing_courses_cache_key,
    lesson_detail_cache_key,
    my_schedule_cache_key,
    purchased_courses_cache_key,
)
from .utils.queryset_utils import get_homework_or_404, get_lesson_or_404

logger = logging.getLogger(__name__)


def _get_is_enrolled(user, course):
    if not user.is_authenticated:
        return False
    if user.is_moderator() or user.is_teacher():
        return True
    return user.is_enrolled(course)


@extend_schema_view(
    list=extend_schema(
        summary="Список курсов на лендинге",
        description="Публичный список опубликованных курсов. Используется на главной странице сайта.",
        tags=["Landing"],
        responses={
            200: CourseListResponseSerializer,
            500: {"schema": SCHEMA_DETAIL},
        },
    ),
)
class CourseDTOList(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CourseDTOSerializer

    def get_queryset(self):
        return Course.objects.filter(
            is_deleted=False, type=Course.PUBLISHED_STATUS, is_special=False
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def list(self, request, *args, **kwargs):
        cache = caches["default"]
        key = landing_courses_cache_key()
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = {"number_of_courses": len(serializer.data), "data": serializer.data}
        cache.set(key, data)
        return Response(data)


class CourseListView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseStoreDTOSerializer

    @extend_schema(
        summary="Список курсов в магазине",
        description=(
            "Возвращает список курсов с учётом роли пользователя. "
            "Модератор видит все курсы. Преподаватель — опубликованные и собственные. "
            "Студент — только опубликованные публичные."
        ),
        tags=["Course"],
        responses={
            200: CourseStoreDTOSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request):
        cache = caches["default"]
        key = course_list_cache_key(request.user.id)
        cached = cache.get(key)
        if cached is not None:
            if isinstance(cached, list) and cached and all(
                isinstance(item, dict) for item in cached
            ):
                if any("is_enrolled" not in item for item in cached):
                    user = request.user
                    if user.is_moderator() or user.is_teacher():
                        patched = [{**item, "is_enrolled": True} for item in cached]
                    else:
                        purchased_ids = {
                            str(course_id) for course_id in user.get_purchased_courses_ids()
                        }
                        patched = [
                            {
                                **item,
                                "is_enrolled": str(item.get("course_id", "")) in purchased_ids,
                            }
                            for item in cached
                        ]
                    cache.set(key, patched)
                    return Response(patched)
            return Response(cached)

        user = request.user
        if user.is_moderator():
            qs = Course.objects.filter(is_deleted=False)
        elif user.is_teacher():
            qs = (
                Course.objects.filter(is_deleted=False)
                .filter(Q(type=Course.PUBLISHED_STATUS) | Q(authors=user))
                .distinct()
            )
        else:
            qs = Course.objects.filter(
                is_deleted=False, type=Course.PUBLISHED_STATUS, is_special=False
            )

        serializer = CourseStoreDTOSerializer(qs, many=True, context={"request": request})
        cache.set(key, serializer.data)
        return Response(serializer.data)

    @extend_schema(
        summary="Создать курс",
        description="Создаёт новый курс. Доступно только модератору.",
        tags=["Course"],
        request=CourseSerializer,
        responses={
            201: CourseSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(last_modified_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseSerializer

    @extend_schema(
        summary="Карточка курса",
        description=(
            "Возвращает полную информацию о курсе по slug. "
            "Неопубликованный курс видят только модератор, автор и записавшийся студент."
        ),
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
        ],
        responses={
            200: CourseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            404: ServiceErrorResponseSerializer,
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_deleted=False)
        user = request.user

        can_see_unpublished = user.is_authenticated and (
            user.is_moderator() or user.is_course_author(course) or user.is_enrolled(course)
        )
        if course.type != Course.PUBLISHED_STATUS and not can_see_unpublished:
            return process_error_response(CourseNotPublished())

        cache = caches["default"]
        key = course_detail_cache_key(slug)
        cacheable = course.type == Course.PUBLISHED_STATUS and not course.is_special

        if cacheable:
            cached = cache.get(key)
            if cached is not None:
                cached["is_enrolled"] = _get_is_enrolled(request.user, course)
                return Response(cached)

        data = CourseSerializer(course, context={"request": request}).data
        if cacheable:
            cache.set(key, {k: v for k, v in data.items() if k != "is_enrolled"})
        return Response(data)

    @extend_schema(
        summary="Обновить курс",
        description="Частичное обновление курса по slug. Доступно только модератору.",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
        ],
        request=CourseSerializer,
        responses={
            200: CourseSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def patch(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_deleted=False)
        serializer = CourseSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(last_modified_by=request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить курс",
        description="Мягкое удаление курса (is_deleted=true). Доступно только модератору.",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_moderator
    def delete(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_deleted=False)
        course.is_deleted = True
        course.save(update_fields=["is_deleted"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyCourses(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Мои курсы",
        description="Список курсов, на которые записан текущий пользователь.",
        tags=["Home"],
        responses={
            200: CourseDTOSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request):
        cache = caches["default"]
        key = purchased_courses_cache_key(request.user.id)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)
        serializer = CourseDTOSerializer(get_courses_for_user(request.user), many=True)
        cache.set(key, serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyScheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Моё расписание",
        description=(
            "Список ближайших событий: вебинаров и дедлайнов домашних заданий. "
            "Без фильтров возвращает все предстоящие события. "
            "Для студента в объектах типа homework указывается статус попытки."
        ),
        tags=["Home"],
        parameters=[
            OpenApiParameter(
                "start_date",
                OpenApiTypes.DATETIME,
                OpenApiParameter.QUERY,
                required=False,
                description="Начало диапазона в формате ISO 8601, например 2024-09-01T00:00:00Z",
            ),
            OpenApiParameter(
                "end_date",
                OpenApiTypes.DATETIME,
                OpenApiParameter.QUERY,
                required=False,
                description="Конец диапазона в формате ISO 8601",
            ),
        ],
        responses={
            200: ScheduleResponseSerializer,
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request):
        start_date = None
        end_date = None
        raw_start = request.query_params.get("start_date")
        raw_end = request.query_params.get("end_date")
        if raw_start:
            start_date = parse_datetime(raw_start)
            if start_date is None:
                return process_error_response(ScheduleDateInvalid(details={"field": "start_date"}))
        if raw_end:
            end_date = parse_datetime(raw_end)
            if end_date is None:
                return process_error_response(ScheduleDateInvalid(details={"field": "end_date"}))

        cache = caches["default"]
        key = my_schedule_cache_key(request.user.id, start_date, end_date)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)

        user = request.user
        authored_ids = set()
        enrolled_ids = set()

        if not user.is_moderator():
            authored_ids = set(
                Course.objects.filter(authors=user).values_list("course_id", flat=True)
            )
            enrolled_ids = set(user.get_purchased_courses_ids())

        webinar_qs = Webinar.objects.select_related("lesson__section__course")
        homework_qs = Homework.objects.select_related("lesson__section__course")

        if not user.is_moderator():
            only_enrolled = enrolled_ids - authored_ids
            published_chain = published_lesson_hierarchy_q()

            webinar_q = Q(lesson__section__course_id__in=authored_ids)
            if only_enrolled:
                webinar_q |= Q(lesson__section__course_id__in=only_enrolled) & published_chain
            webinar_qs = webinar_qs.filter(webinar_q)

            homework_q = Q(lesson__section__course_id__in=authored_ids)
            if only_enrolled:
                homework_q |= Q(lesson__section__course_id__in=only_enrolled) & published_chain
            homework_qs = homework_qs.filter(homework_q)

        webinar_qs = webinar_qs.exclude(scheduled_at=None, started_at=None)
        homework_qs = homework_qs.exclude(deadline=None)

        if start_date:
            webinar_qs = webinar_qs.filter(
                Q(scheduled_at__gte=start_date) | Q(scheduled_at=None, started_at__gte=start_date)
            )
            homework_qs = homework_qs.filter(deadline__gte=start_date)
        if end_date:
            webinar_qs = webinar_qs.filter(
                Q(scheduled_at__lte=end_date) | Q(scheduled_at=None, started_at__lte=end_date)
            )
            homework_qs = homework_qs.filter(deadline__lte=end_date)

        attempt_map = {}
        if user.is_student():
            from apps.homeworks.models import Attempt

            homework_ids = list(homework_qs.values_list("homework_id", flat=True))
            attempts = Attempt.objects.filter(user=user, homework_id__in=homework_ids).values(
                "homework_id", "status"
            )
            attempt_map = {str(a["homework_id"]): a["status"] for a in attempts}

        items = []
        for webinar in webinar_qs:
            course = webinar.lesson.section.course
            effective_dt = webinar.scheduled_at or webinar.started_at
            items.append(
                {
                    "type": ScheduleItemSerializer.TYPE_WEBINAR,
                    "datetime": effective_dt,
                    "course_title": course.title,
                    "course_slug": course.slug,
                    "title": webinar.lesson.title,
                    "webinar_id": webinar.webinar_id,
                    "lesson_slug": webinar.lesson.slug,
                    "webinar_status": webinar.status,
                    "scheduled_at": webinar.scheduled_at,
                }
            )
        for homework in homework_qs:
            course = homework.lesson.section.course
            attempt_status = (
                attempt_map.get(str(homework.homework_id), "not_started")
                if user.is_student()
                else None
            )
            items.append(
                {
                    "type": ScheduleItemSerializer.TYPE_HOMEWORK,
                    "datetime": homework.deadline,
                    "course_title": course.title,
                    "course_slug": course.slug,
                    "title": homework.title,
                    "homework_id": homework.homework_id,
                    "homework_slug": homework.slug,
                    "homework_lesson_slug": homework.lesson.slug,
                    "deadline": homework.deadline,
                    "attempt_status": attempt_status,
                }
            )

        items.sort(key=lambda x: x["datetime"])
        data = {"items": items}
        cache.set(key, data)
        return Response(data)


class CourseHomePageView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Главная страница курса",
        description=(
            "Структура курса с секциями и уроками. "
            "Требует записи на курс. Преподаватель и модератор видят черновики."
        ),
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
        ],
        responses={
            200: CourseHomeSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: ServiceErrorResponseSerializer,
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        user = request.user
        vis = course_content_visibility(user, course)

        if not vis.has_course_home_access():
            return process_error_response(NotEnrolled())

        serializer = CourseHomeSerializer(
            course,
            context={"is_author": vis.show_types_in_tree, "request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


def _get_section_or_404(course_slug, section_slug):
    return get_object_or_404(Section, course__slug=course_slug, slug=section_slug)


def _get_task_or_404(course_slug, lesson_slug, homework_slug, task_id):
    return get_object_or_404(
        Task,
        task_id=task_id,
        homework__slug=homework_slug,
        homework__lesson__slug=lesson_slug,
        homework__lesson__section__course__slug=course_slug,
    )


def _get_question_or_404(course_slug, lesson_slug, homework_slug, question_id):
    return get_object_or_404(
        Question,
        question_id=question_id,
        homework__slug=homework_slug,
        homework__lesson__slug=lesson_slug,
        homework__lesson__section__course__slug=course_slug,
    )


class SectionCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SectionSerializer

    @extend_schema(
        summary="Создать секцию",
        description="Добавляет секцию в курс. Доступно автору курса и модератору.",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
        ],
        request=SectionSerializer,
        responses={
            201: SectionSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        payload = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        payload["course"] = course.course_id
        serializer = SectionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SectionDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SectionSerializer

    @extend_schema(
        summary="Обновить секцию",
        description="Частичное обновление секции. Доступно автору курса и модератору.",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "section_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug секции"
            ),
        ],
        request=SectionSerializer,
        responses={
            200: SectionSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def patch(self, request, course_slug, section_slug):
        section = _get_section_or_404(course_slug, section_slug)
        serializer = SectionSerializer(section, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить секцию",
        description="Удаляет секцию вместе со всеми уроками. Доступно автору курса и модератору.",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "section_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug секции"
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def delete(self, request, course_slug, section_slug):
        section = _get_section_or_404(course_slug, section_slug)
        section.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LessonCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    @extend_schema(
        methods=["POST"],
        summary="Создать урок",
        description=(
            "Создаёт урок в указанном курсе. "
            "Передавать контент (поле content) здесь нельзя — используйте PUT для обновления урока с контентом."
        ),
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
        ],
        request=LessonSimpleCreateSerializer,
        responses={
            201: LessonSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        serializer = LessonSimpleCreateSerializer(
            data=request.data,
            context={"request": request, "course": course},
        )
        serializer.is_valid(raise_exception=True)
        lesson = serializer.save()
        return Response(
            LessonSerializer(lesson).data,
            status=status.HTTP_201_CREATED,
        )


class LessonDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    serializer_class = LessonSerializer

    @extend_schema(
        summary="Получить урок",
        description=(
            "Возвращает полное содержимое урока: текст, вебинар, записи и домашние задания. "
            "Требует записи на курс."
        ),
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
        ],
        responses={
            200: LessonDetailReadSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_enrollment
    def get(self, request, course_slug, lesson_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        vis = course_content_visibility(request.user, course)
        key = lesson_detail_cache_key(
            course_slug,
            lesson_slug,
            vis.cache_scope,
            user_id=request.user.pk,
        )
        return cached_detail_response(
            key,
            lambda: LessonDetailReadSerializer(
                get_lesson_or_404(course_slug, lesson_slug, include_drafts=vis.include_drafts),
                context={"include_drafts": vis.include_drafts, "request": request},
            ).data,
        )

    @extend_schema(
        summary="Обновить урок",
        description=(
            "Полное обновление урока: заголовок, тип, секция и контент. "
            "Поле content принимает JSON-документ редактора."
        ),
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
        ],
        request=LessonCreateSerializer,
        responses={
            200: LessonCreateSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def put(self, request, course_slug, lesson_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        lesson = get_lesson_or_404(course_slug, lesson_slug, include_drafts=True)
        serializer = LessonCreateSerializer(
            lesson,
            data=request.data,
            partial=True,
            context={"request": request, "course": course},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить урок",
        description="Удаляет урок вместе с домашними заданиями. Доступно автору курса и модератору.",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug):
        lesson = get_lesson_or_404(course_slug, lesson_slug, include_drafts=True)
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HomeworkCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Создать домашнее задание",
        description="Создаёт домашнее задание к уроку. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
        ],
        request=HomeworkSerializer,
        responses={
            201: HomeworkDetailSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        lesson = get_lesson_or_404(course_slug, lesson_slug, include_drafts=True)
        serializer = HomeworkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        homework = serializer.save(lesson=lesson)
        response_serializer = HomeworkDetailSerializer(homework)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class HomeworkDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Получить домашнее задание",
        description=(
            "Возвращает домашнее задание с вопросами и задачами. " "Требует записи на курс."
        ),
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
        ],
        responses={
            200: HomeworkDetailSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_enrollment
    def get(self, request, course_slug, lesson_slug, homework_slug):
        course = get_object_or_404(Course, slug=course_slug, is_deleted=False)
        vis = course_content_visibility(request.user, course)
        key = homework_detail_cache_key(course_slug, lesson_slug, homework_slug, vis.cache_scope)
        return cached_detail_response(
            key,
            lambda: HomeworkDetailSerializer(
                get_homework_or_404(
                    course_slug,
                    lesson_slug,
                    homework_slug,
                    include_drafts=vis.include_drafts,
                )
            ).data,
        )

    @extend_schema(
        summary="Обновить домашнее задание",
        description="Частичное обновление домашнего задания. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
        ],
        request=HomeworkSerializer,
        responses={
            200: HomeworkDetailSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def patch(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(course_slug, lesson_slug, homework_slug, include_drafts=True)
        serializer = HomeworkSerializer(homework, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        homework = serializer.save()
        response_serializer = HomeworkDetailSerializer(homework)
        return Response(response_serializer.data)

    @extend_schema(
        summary="Удалить домашнее задание",
        description="Удаляет домашнее задание вместе с вопросами и задачами. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(course_slug, lesson_slug, homework_slug, include_drafts=True)
        homework.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskSerializer

    @extend_schema(
        summary="Создать задачу с развёрнутым ответом",
        description="Добавляет задачу к домашнему заданию. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
        ],
        request=TaskSerializer,
        responses={
            201: TaskSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(course_slug, lesson_slug, homework_slug, include_drafts=True)
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(homework=homework)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskSerializer

    @extend_schema(
        summary="Обновить задачу с развёрнутым ответом",
        description="Частичное обновление задачи. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
            OpenApiParameter(
                "task_id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="UUID задачи"
            ),
        ],
        request=TaskSerializer,
        responses={
            200: TaskSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def patch(self, request, course_slug, lesson_slug, homework_slug, task_id):
        task = _get_task_or_404(course_slug, lesson_slug, homework_slug, task_id)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить задачу с развёрнутым ответом",
        description="Удаляет задачу из домашнего задания. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
            OpenApiParameter(
                "task_id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="UUID задачи"
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug, homework_slug, task_id):
        task = _get_task_or_404(course_slug, lesson_slug, homework_slug, task_id)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionCreateView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = QuestionSerializer

    @extend_schema(
        summary="Создать вопрос с вариантами ответа",
        description="Добавляет вопрос с вариантами к домашнему заданию. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
        ],
        request=QuestionSerializer,
        responses={
            201: QuestionSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(course_slug, lesson_slug, homework_slug, include_drafts=True)
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(homework=homework)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyContentView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Мой контент",
        description=(
            "Список курсов с уроками, доступными текущему пользователю. "
            "Студент видит опубликованные уроки купленных курсов. "
            "Преподаватель — свои курсы со всеми уроками, включая черновики. "
            "Модератор — все курсы без ограничений."
        ),
        tags=["Home"],
        responses={
            200: MyContentCourseSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request):
        user = request.user
        courses = get_courses_for_user(user)
        serializer = MyContentCourseSerializer(
            courses,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class QuestionDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = QuestionSerializer

    @extend_schema(
        summary="Обновить вопрос с вариантами ответа",
        description="Частичное обновление вопроса. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
            OpenApiParameter(
                "question_id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="UUID вопроса"
            ),
        ],
        request=QuestionSerializer,
        responses={
            200: QuestionSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def patch(self, request, course_slug, lesson_slug, homework_slug, question_id):
        question = _get_question_or_404(course_slug, lesson_slug, homework_slug, question_id)
        serializer = QuestionSerializer(question, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить вопрос с вариантами ответа",
        description="Удаляет вопрос из домашнего задания. Доступно автору курса и модератору.",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                "course_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug курса"
            ),
            OpenApiParameter(
                "lesson_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Slug урока"
            ),
            OpenApiParameter(
                "homework_slug",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="Slug домашнего задания",
            ),
            OpenApiParameter(
                "question_id", OpenApiTypes.UUID, OpenApiParameter.PATH, description="UUID вопроса"
            ),
        ],
        responses={
            204: None,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug, homework_slug, question_id):
        question = _get_question_or_404(course_slug, lesson_slug, homework_slug, question_id)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
