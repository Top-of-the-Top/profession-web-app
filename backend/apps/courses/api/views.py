from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
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
    LessonDetailReadSerializer,
    HomeworkSerializer,
    HomeworkDetailSerializer,
    CourseHomeSerializer,
    SectionSerializer,
    TaskSerializer,
    QuestionSerializer,
)
from .agora_utils import (
    generate_rtc_token, user_uid_from_uuid, create_whiteboard_room, generate_whiteboard_room_token, 
    recording_acquire, recording_start, recording_stop, ROLE_PUBLISHER, ROLE_SUBSCRIBER,
)
from rest_framework import generics
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from apps.users.api.decorators import require_moderator, require_course_author, require_course_enrollment
from django.core.cache import caches
from django.utils import timezone
import os

from .schema import SCHEMA_DETAIL, SCHEMA_VALIDATION


def landing_courses_cache_key():
    return "default:landing:courses:list"

def course_list_cache_key():
    return "default:app:courses:list"

def course_detail_cache_key(slug):
    return f"default:courses:detail:{slug}"

def purchased_courses_cache_key(user_id):
    return f"default:courses:purchased:{int(user_id)}"

def section_list_cache_key(course_slug):
    return f"default:sections:list:{course_slug}"

def section_detail_cache_key(course_slug, slug):
    return f"default:sections:detail:{course_slug}:{slug}"

def lesson_list_cache_key(course_slug):
    return f"default:lessons:list:{course_slug}"

def lesson_detail_cache_key(course_slug, slug):
    return f"default:lessons:detail:{course_slug}:{slug}"

def homework_detail_cache_key(course_slug, lesson_slug, slug):
    return f"default:homeworks:detail:{course_slug}:{lesson_slug}:{slug}"

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
        purchased = PurchasedCourse.objects.filter(
            user=request.user,
        ).select_related('course', 'payment')
        serializer = PurchasedCourseSerializer(purchased, many=True)
        cache.set(key, serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

        is_moderator = user.is_moderator()
        is_author = user.is_teacher() and user.is_course_author(course)
        is_enrolled = user.is_enrolled(course)

        if not (is_enrolled or is_author or is_moderator):
            return Response(
                {'detail': 'Вы не записаны на этот курс'},
                status=status.HTTP_403_FORBIDDEN
            )

        show_type = is_author or is_moderator

        serializer = CourseHomeSerializer(
            course,
            context={'is_author': show_type}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


def _lesson_queryset_for_course(course_slug):
    hw_qs = Homework.objects.order_by('homework_number', 'created_at')
    return (
        Lesson.objects.filter(section__course__slug=course_slug)
        .select_related('section', 'section__course')
        .prefetch_related(Prefetch('homework_set', queryset=hw_qs))
        .order_by('lesson_number')
    )


def _get_lesson_or_404(course_slug, lesson_slug):
    return get_object_or_404(_lesson_queryset_for_course(course_slug), slug=lesson_slug)


def _homework_queryset_for_lesson(course_slug, lesson_slug):
    return (
        Homework.objects.filter(
            lesson__slug=lesson_slug,
            lesson__section__course__slug=course_slug,
        )
        .select_related('lesson')
        .prefetch_related('question_set', 'task_set')
        .order_by('homework_number')
    )


def _get_homework_or_404(course_slug, lesson_slug, homework_slug):
    return get_object_or_404(_homework_queryset_for_lesson(course_slug, lesson_slug), slug=homework_slug)


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
    serializer_class = LessonSerializer

    @extend_schema(
        summary="Создать урок",
        tags=["Course"],
        request=LessonSerializer,
        responses={
            201: LessonSerializer,
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
        serializer = LessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = serializer.validated_data.get('section')
        if section is not None and section.course_id != course.course_id:
            return Response(
                {'detail': 'Секция не принадлежит этому курсу.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LessonDetailView(APIView):
    permission_classes = (IsAuthenticated,)
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
        cache = caches["default"]
        key = lesson_detail_cache_key(course_slug, lesson_slug)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        lesson = _get_lesson_or_404(course_slug, lesson_slug)
        data = LessonDetailReadSerializer(lesson).data
        cache.set(key, data)
        return Response(data)

    @extend_schema(
        summary="Обновить урок",
        tags=["Course"],
        parameters=[
            OpenApiParameter(
                name='lesson_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        request=LessonSerializer,
        responses={
            200: LessonSerializer,
            400: {"schema": SCHEMA_VALIDATION},
            401: {"schema": SCHEMA_DETAIL},
            403: {"schema": SCHEMA_DETAIL},
            404: {"schema": SCHEMA_DETAIL},
            500: {"schema": SCHEMA_DETAIL},
        }
    )
    @require_course_author
    def patch(self, request, course_slug, lesson_slug):
        lesson = _get_lesson_or_404(course_slug, lesson_slug)
        serializer = LessonSerializer(lesson, data=request.data, partial=True)
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
        lesson = _get_lesson_or_404(course_slug, lesson_slug)
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
        lesson = _get_lesson_or_404(course_slug, lesson_slug)
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
        cache = caches["default"]
        key = homework_detail_cache_key(course_slug, lesson_slug, homework_slug)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        homework = _get_homework_or_404(course_slug, lesson_slug, homework_slug)
        data = HomeworkDetailSerializer(homework).data
        cache.set(key, data)
        return Response(data)

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
        homework = _get_homework_or_404(course_slug, lesson_slug, homework_slug)
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
        homework = _get_homework_or_404(course_slug, lesson_slug, homework_slug)
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
        homework = _get_homework_or_404(course_slug, lesson_slug, homework_slug)
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
        homework = _get_homework_or_404(course_slug, lesson_slug, homework_slug)
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
        if not course.authors.filter(pk=request.user.pk).exists():
            return Response(
                {'detail': 'Только автор курса может запускать вебинар'},
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
        if not course.authors.filter(pk=request.user.pk).exists():
            return Response(
                {'detail': 'Только автор курса может останавливать вебинар'},
                status=status.HTTP_403_FORBIDDEN,
            )

        webinar = get_object_or_404(Webinar, lesson=lesson)

        if webinar.recording_resource_id and webinar.recording_sid:
            try:
                result = recording_stop(
                    channel_name=webinar.agora_channel_name,
                    uid='1',
                    resource_id=webinar.recording_resource_id,
                    sid=webinar.recording_sid,
                )
                server_response = result.get('serverResponse', {})
                file_list = server_response.get('fileList', [])
                if file_list:
                    webinar.recording_url = file_list[0].get('fileName', '')
            except Exception:
                pass

        webinar.status = 'ended'
        webinar.ended_at = timezone.now()
        webinar.save()

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

        is_teacher = course.authors.filter(pk=request.user.pk).exists()
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


class WebinarRecordingStartView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_slug, lesson_slug):
        lesson = get_object_or_404(
            Lesson.objects.select_related('section__course'),
            slug=lesson_slug,
            section__course__slug=course_slug,
        )
        course = lesson.section.course
        if not course.authors.filter(pk=request.user.pk).exists():
            return Response(status=status.HTTP_403_FORBIDDEN)

        webinar = get_object_or_404(Webinar, lesson=lesson, status='live')
        recording_uid = '1'

        resource_id = recording_acquire(
            channel_name=webinar.agora_channel_name,
            uid=recording_uid,
        )

        recording_token = generate_rtc_token(
            channel_name=webinar.agora_channel_name,
            uid=int(recording_uid),
            role=ROLE_SUBSCRIBER,
        )

        sid = recording_start(
            channel_name=webinar.agora_channel_name,
            uid=recording_uid,
            resource_id=resource_id,
            token=recording_token,
        )

        webinar.recording_resource_id = resource_id
        webinar.recording_sid = sid
        webinar.save()

        return Response({'detail': 'Запись началась'})
