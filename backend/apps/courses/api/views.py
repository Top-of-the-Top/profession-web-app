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
from apps.webinars.models import Webinar

from ..models import Course, Homework, Question, Section, Task
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


@extend_schema_view(
    list=extend_schema(
        summary="Лендинг: список курсов",
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
        return Course.objects.filter(is_deleted=False, type=Course.PUBLISHED_STATUS)

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
    serializer_class = CourseSerializer

    @extend_schema(
        summary="Список курсов",
        tags=["Course"],
        responses={
            200: CourseSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request):
        cache = caches["default"]
        key = course_list_cache_key(request.user.id)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)

        user = request.user
        if user.is_moderator():
            qs = Course.objects.filter(is_deleted=False)
        elif user.is_teacher():
            qs = (
                Course.objects.filter(
                    is_deleted=False,
                )
                .filter(Q(type=Course.PUBLISHED_STATUS) | Q(authors=user))
                .distinct()
            )
        else:
            qs = Course.objects.filter(is_deleted=False, type=Course.PUBLISHED_STATUS)

        serializer = CourseSerializer(qs, many=True, context={"request": request})
        cache.set(key, serializer.data)
        return Response(serializer.data)

    @extend_schema(
        summary="Создать курс",
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
        summary="Курс по slug",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: CourseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request, slug):
        cache = caches["default"]
        key = course_detail_cache_key(slug)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        course = get_object_or_404(Course, slug=slug, is_deleted=False)
        data = CourseSerializer(course).data
        cache.set(key, data)
        return Response(data)

    @extend_schema(
        summary="Обновить курс",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        summary="Расписание по моим курсам",
        description=(
            "Возвращает список объектов расписания (вебинары и дедлайны домашних заданий) "
            "в заданном диапазоне дат. "
            "Студент видит объекты своих купленных курсов. "
            "Преподаватель видит объекты своих курсов (в том числе черновики). "
            "Модератор видит всё."
        ),
        tags=["Home"],
        parameters=[
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Начало диапазона (ISO 8601)",
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Конец диапазона (ISO 8601)",
            ),
        ],
        responses={
            200: ScheduleResponseSerializer,
            400: {"schema": SCHEMA_DETAIL},
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
                return Response(
                    {"detail": "Неверный формат start_date"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if raw_end:
            end_date = parse_datetime(raw_end)
            if end_date is None:
                return Response(
                    {"detail": "Неверный формат end_date"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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

        webinar_qs = webinar_qs.exclude(started_at=None)
        homework_qs = homework_qs.exclude(deadline=None)

        if start_date:
            webinar_qs = webinar_qs.filter(started_at__gte=start_date)
            homework_qs = homework_qs.filter(deadline__gte=start_date)
        if end_date:
            webinar_qs = webinar_qs.filter(started_at__lte=end_date)
            homework_qs = homework_qs.filter(deadline__lte=end_date)

        items = []
        for webinar in webinar_qs:
            items.append(
                {
                    "type": ScheduleItemSerializer.TYPE_WEBINAR,
                    "datetime": webinar.started_at,
                    "course_title": webinar.lesson.section.course.title,
                    "title": webinar.lesson.title,
                }
            )
        for homework in homework_qs:
            items.append(
                {
                    "type": ScheduleItemSerializer.TYPE_HOMEWORK,
                    "datetime": homework.deadline,
                    "course_title": homework.lesson.section.course.title,
                    "title": homework.title,
                }
            )

        items.sort(key=lambda x: x["datetime"])
        data = {"items": items}
        cache.set(key, data)
        return Response(data)


class CourseHomePageView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Главная курса",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="course_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: CourseHomeSerializer,
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        user = request.user
        vis = course_content_visibility(user, course)

        if not vis.has_course_home_access():
            return Response(
                {"detail": "Вы не записаны на этот курс"},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        tags=["Course"],
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
        course = get_object_or_404(Course, slug=course_slug)
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
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="section_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="section_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
            "Тело: `section`, `title`, `type` (по умолчанию draft). "
            "Поле `content` в POST не допускается — контент и вложения задаются PUT "
            "на `/api/courses/{slug}/lessons/{lesson_slug}/`."
        ),
        tags=["Course"],
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
        course = get_object_or_404(Course, slug=course_slug)
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
        summary="Урок",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        course = get_object_or_404(Course, slug=course_slug)
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
        summary="Обновить урок (PUT)",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        course = get_object_or_404(Course, slug=course_slug)
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
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name="lesson_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        summary="Создать домашку",
        tags=["Homework"],
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
        summary="Домашка",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="homework_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        course = get_object_or_404(Course, slug=course_slug)
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
        summary="Обновить домашку",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="homework_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        summary="Удалить домашку",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="homework_slug",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
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
        summary="Создать задачу",
        tags=["Homework"],
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
        summary="Обновить задачу",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
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
        summary="Удалить задачу",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
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
        summary="Создать вопрос",
        tags=["Homework"],
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
        summary="Мои курсы с уроками",
        description=(
            "Возвращает курсы пользователя с плоским списком уроков. "
            "Студент видит купленные курсы и опубликованные уроки. "
            "Преподаватель видит свои курсы со всеми уроками (включая черновики). "
            "Модератор видит все курсы со всеми уроками."
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
        summary="Обновить вопрос",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="question_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
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
        summary="Удалить вопрос",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name="question_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
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
