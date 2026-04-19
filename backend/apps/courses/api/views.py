from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from ..models import (
    Course,
    PurchasedCourse,
    Lesson,
    Homework,
    Section,
    Task,
    Question,
    Webinar,
)
from .serializers import (
    CourseDTOSerializer,
    CourseSerializer,
    PurchasedCourseSerializer,
    CourseListResponseSerializer,
    LessonSerializer,
    LessonSimpleCreateSerializer,
    LessonCreateSerializer,
    LessonDetailReadSerializer,
    HomeworkSerializer,
    HomeworkDetailSerializer,
    CourseHomeSerializer,
    SectionSerializer,
    TaskSerializer,
    QuestionSerializer,
    UserWebinarListItemSerializer,
)
from .utils.agora_utils import (
    generate_rtc_token, user_uid_from_uuid, create_whiteboard_room, generate_whiteboard_room_token, 
    recording_acquire, recording_start, recording_start_web, recording_stop, recording_stop_web,
    verify_recorder_token, make_recorder_token,ban_whiteboard_room, ROLE_PUBLISHER, ROLE_SUBSCRIBER,
)
from rest_framework import generics
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from apps.users.api.decorators import require_moderator, require_course_author, require_course_enrollment
from rest_framework.parsers import MultiPartParser
from django.core.cache import caches
from django.db.models import F, Q
from django.utils import timezone
import os
from .schema import SCHEMA_DETAIL, SCHEMA_VALIDATION
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
from .utils.rbac_utils import course_content_visibility, published_lesson_hierarchy_q
import logging

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
        return Course.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        cache = caches["default"]
        key = landing_courses_cache_key()
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = {'number_of_courses': len(serializer.data), 'data': serializer.data}
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
        }
    )
    def get(self, request):
        cache = caches["default"]
        key = course_list_cache_key()
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        queryset = Course.objects.all()
        serializer = CourseSerializer(queryset, many=True)
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
        }
    )
    @require_moderator
    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseSerializer

    @extend_schema(
        summary="Курс по slug",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: CourseSerializer,
            401: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        }
    )
    def get(self, request, slug):
        cache = caches["default"]
        key = course_detail_cache_key(slug)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        course = get_object_or_404(Course, slug=slug)
        data = CourseSerializer(course).data
        cache.set(key, data)
        return Response(data)

    @extend_schema(
        summary="Обновить курс",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
        }
    )
    @require_course_author
    def patch(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        serializer = CourseSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить курс",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
        }
    )
    @require_course_author
    def delete(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchasedCoursesView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Мои покупки",
        tags=["Home"],
        responses={
            200: PurchasedCourseSerializer(many=True),
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
        purchased = (
            PurchasedCourse.objects.filter(user=request.user)
            .filter(
                Q(course__type=Course.PUBLISHED_STATUS)
                | Q(course__authors=request.user)
            )
            .distinct()
            .select_related('course', 'payment')
        )
        serializer = PurchasedCourseSerializer(purchased, many=True)
        cache.set(key, serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyScheduleView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Расписание вебинаров по моим курсам",
        tags=["Home"],
        responses={
            200: UserWebinarListItemSerializer(many=True),
            401: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        },
    )
    def get(self, request):
        cache = caches["cold"]
        key = my_schedule_cache_key(request.user.id)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        user = request.user
        qs = Webinar.objects.all()
        if not user.is_moderator():
            authored_ids = set(
                Course.objects.filter(authors=user).values_list('course_id', flat=True)
            )
            enrolled_ids = set(user.get_purchased_courses_ids())
            only_enrolled = enrolled_ids - authored_ids
            published_chain = published_lesson_hierarchy_q()
            q = Q(lesson__section__course_id__in=authored_ids)
            if only_enrolled:
                q |= Q(lesson__section__course_id__in=only_enrolled) & published_chain
            qs = qs.filter(q)

        rows = (
            qs.values(
                'started_at',
                'ended_at',
                course_title=F('lesson__section__course__title'),
                course_slug=F('lesson__section__course__slug'),
                lesson_title=F('lesson__title'),
                lesson_slug=F('lesson__slug'),
            )
            .order_by(F('started_at').desc(nulls_last=True), '-created_at')
        )
        data = list(rows)
        cache.set(key, data)
        return Response(data)


class CourseHomePageView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Главная курса",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='course_slug',
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
        }
    )
    def get(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        user = request.user
        vis = course_content_visibility(user, course)

        if not vis.has_course_home_access():
            return Response(
                {'detail': 'Вы не записаны на этот курс'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CourseHomeSerializer(
            course,
            context={'is_author': vis.show_types_in_tree},
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
        }
    )
    @require_course_author
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        payload = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        payload['course'] = course.course_id
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
                name='section_slug',
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
        }
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
                name='section_slug',
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
        }
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
        methods=['POST'],
        summary='Создать урок',
        description=(
            'Тело: `section`, `title`, `type` (по умолчанию draft). '
            'Поле `content` в POST не допускается — контент и вложения задаются PUT '
            'на `/api/courses/{slug}/lessons/{lesson_slug}/`.'
        ),
        tags=['Course'],
        request=LessonSimpleCreateSerializer,
        responses={
            201: LessonSerializer,
            400: {'schema': SCHEMA_VALIDATION},
            401: {'schema': SCHEMA_DETAIL},
            403: {'schema': SCHEMA_DETAIL},
            404: {'schema': SCHEMA_DETAIL},
            500: {'schema': SCHEMA_DETAIL},
        },
    )
    @require_course_author
    def post(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        serializer = LessonSimpleCreateSerializer(
            data=request.data,
            context={'request': request, 'course': course},
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
                name='lesson_slug',
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
        }
    )
    @require_course_enrollment
    def get(self, request, course_slug, lesson_slug):
        course = get_object_or_404(Course, slug=course_slug)
        vis = course_content_visibility(request.user, course)
        key = lesson_detail_cache_key(course_slug, lesson_slug, vis.cache_scope)
        return cached_detail_response(
            key,
            lambda: LessonDetailReadSerializer(
                get_lesson_or_404(
                    course_slug, lesson_slug, include_drafts=vis.include_drafts
                ),
                context={'include_drafts': vis.include_drafts},
            ).data,
        )

    @extend_schema(
        summary="Обновить урок (PUT)",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='lesson_slug',
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
        }
    )
    @require_course_author
    def put(self, request, course_slug, lesson_slug):
        course = get_object_or_404(Course, slug=course_slug)
        lesson = get_lesson_or_404(course_slug, lesson_slug, include_drafts=True)
        serializer = LessonCreateSerializer(
            lesson,
            data=request.data,
            partial=True,
            context={'request': request, 'course': course},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Удалить урок",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='lesson_slug',
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
        }
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
        }
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
                name='homework_slug',
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
        }
    )
    @require_course_enrollment
    def get(self, request, course_slug, lesson_slug, homework_slug):
        course = get_object_or_404(Course, slug=course_slug)
        vis = course_content_visibility(request.user, course)
        key = homework_detail_cache_key(
            course_slug, lesson_slug, homework_slug, vis.cache_scope
        )
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
                name='homework_slug',
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
        }
    )
    @require_course_author
    def patch(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(
            course_slug, lesson_slug, homework_slug, include_drafts=True
        )
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
                name='homework_slug',
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
        }
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(
            course_slug, lesson_slug, homework_slug, include_drafts=True
        )
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
        }
    )
    @require_course_author
    def post(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(
            course_slug, lesson_slug, homework_slug, include_drafts=True
        )
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
                name='task_id',
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
        }
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
                name='task_id',
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
        }
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
        }
    )
    @require_course_author
    def post(self, request, course_slug, lesson_slug, homework_slug):
        homework = get_homework_or_404(
            course_slug, lesson_slug, homework_slug, include_drafts=True
        )
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(homework=homework)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestionDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = QuestionSerializer

    @extend_schema(
        summary="Обновить вопрос",
        tags=["Homework"],
        parameters=[
            OpenApiParameter(
                name='question_id',
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
        }
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
                name='question_id',
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
        }
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug, homework_slug, question_id):
        question = _get_question_or_404(course_slug, lesson_slug, homework_slug, question_id)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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

        webinar, created = Webinar.objects.get_or_create(
            lesson=lesson,
            started_by=request.user,
        )

        if webinar.status == 'live':
            return Response(
                {'detail': 'Вебинар уже запущен'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not webinar.whiteboard_room_uuid:
            try:
                webinar.whiteboard_room_uuid = create_whiteboard_room()
            except Exception:
                return Response(
                    {'detail': 'Не удалось создать комнату доски. Попробуйте позже.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        webinar.status = 'live'
        webinar.started_by = request.user
        webinar.started_at = timezone.now()
        webinar.recording_resource_id = ''
        webinar.recording_sid = ''
        webinar.ended_at = None
        webinar.kinescope_video_id = ''
        webinar.kinescope_upload_status = 'none'
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
                logger.exception("Ошибка при остановке записи вебинара %s", webinar.id)

        webinar.status = 'ended'
        webinar.ended_at = timezone.now()
        webinar.save()

        if webinar.recording_url:
            from ..tasks import upload_recording_to_kinescope
            webinar.kinescope_upload_status = 'pending'
            webinar.save(update_fields=['kinescope_upload_status'])
            upload_recording_to_kinescope.delay(str(webinar.webinar_id))

        if webinar.whiteboard_room_uuid:
            try:
                ban_whiteboard_room(webinar.whiteboard_room_uuid)
            except Exception:
                logger.exception("Ошибка при закрытии комнаты доски %s", webinar.whiteboard_room_uuid)

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

        webinar = get_object_or_404(Webinar, lesson=lesson, status='live')
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

        webinar.recording_resource_id = resource_id
        webinar.recording_sid = sid
        webinar.save()

        return Response({'detail': 'Запись началась'})


class WebinarWhiteboardPdfView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

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

        webinar = get_object_or_404(Webinar, lesson=lesson)

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

        pdf_path = f'whiteboards/webinar_{webinar.webinar_id}.pdf'
        saved_path = default_storage.save(pdf_path, ContentFile(pdf_bytes))

        bucket = os.getenv('AWS_S3_BUCKET_NAME')
        webinar.whiteboard_pdf_url = (f'https://storage.yandexcloud.net/{bucket}/{saved_path}')
        webinar.save(update_fields=['whiteboard_pdf_url'])

        return Response({'detail': 'pdf доски сохранен'})
    

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
            webinar = Webinar.objects.select_related('lesson__section__course').get(kinescope_video_id=video_id)
        except Webinar.DoesNotExist:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=user_id)
            course = webinar.lesson.section.course
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
        