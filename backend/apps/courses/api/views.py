from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from ..models import Course, PurchasedCourse, Lesson, Homework, Section, Task, Question
from .serializers import (
    CourseDTOSerializer,
    CourseSerializer,
    PurchasedCourseSerializer,
    CourseListResponseSerializer,
    LessonSerializer,
    HomeworkSerializer,
    HomeworkCreateSerializer,
    CourseHomePageSerializer,
    SectionSerializer,
    TaskSerializer,
    QuestionSerializer,
)
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.users.api.decorators import require_moderator, require_course_author, require_course_enrollment
from django.core.cache import caches

SCHEMA_401 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Сообщение об ошибке аутентификации.",
            "example": "Authentication credentials were not provided.",
        }
    },
}
SCHEMA_COURSE_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Курс не найден.",
            "example": "Курс не найден",
        }
    },
}

SCHEMA_LESSON_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Урок не найден.",
            "example": "Урок не найден",
        }
    },
}
SCHEMA_LESSON_500 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Внутренняя ошибка сервера.",
            "example": "Произошла ошибка при обработке запроса.",
        }
    },
}

SCHEMA_HOMEWORK_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Домашнее задание не найдено.",
            "example": "Домашнее задание не найдено",
        }
    },
}
SCHEMA_HOMEWORK_500 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Внутренняя ошибка сервера.",
            "example": "Произошла ошибка при обработке запроса.",
        }
    },
}

SCHEMA_SECTION_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Секция не найдена.",
            "example": "Секция не найдена",
        }
    },
}

SCHEMA_SECTION_500 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Внутренняя ошибка сервера.",
            "example": "Произошла ошибка при обработке запроса.",
        }
    },
}

SCHEMA_TASK_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Задача не найдена.",
            "example": "Задача не найдена",
        }
    },
}

SCHEMA_QUESTION_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Вопрос не найден.",
            "example": "Вопрос не найден",
        }
    },
}

SCHEMA_403 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Доступ запрещен.",
            "example": "Доступ запрещен. Требуется роль: moderator",
        }
    },
}

SCHEMA_COURSE_500 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Внутренняя ошибка сервера.",
            "example": "Произошла ошибка при обработке запроса.",
        }
    },
}

def landing_courses_cache_key():
    return "default:courses:list"

def course_list_cache_key():
    return "default:courses:list"

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

def homework_list_cache_key(course_slug, lesson_slug):
    return f"default:homeworks:list:{course_slug}:{lesson_slug}"

def homework_detail_cache_key(course_slug, lesson_slug, slug):
    return f"default:homeworks:detail:{course_slug}:{lesson_slug}:{slug}"

class CourseDTOList(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CourseDTOSerializer

    def get_queryset(self):
        return Course.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @extend_schema(
        summary="Список курсов (лендинг)",
        description=(
            "Публичный список всех курсов для лендинга. Авторизация не требуется. "
            "Возвращается объект: number_of_courses (число курсов) и data — массив курсов в формате DTO (course_id, title, sub_title, image_url, price, slug)."
        ),
        tags=["Landing"],
        responses={200: CourseListResponseSerializer},
    )
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
        summary="Список всех курсов",
        description=(
            "Возвращает список всех курсов. Доступно всем авторизованным пользователям. "
            "Права доступа: Студент - просмотр, Учитель - просмотр, Модератор - просмотр."
        ),
        tags=["Courses"],
        responses={
            200: CourseSerializer(many=True),
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_COURSE_500},
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
        summary="Создать новый курс",
        description=(
            "Создает новый курс. Доступно только модераторам. "
            "Права доступа: Студент - запрещено, Учитель - запрещено, Модератор - разрешено."
        ),
        tags=["Courses"],
        responses={
            201: CourseSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен. Требуется роль модератора.", "schema": SCHEMA_403},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_COURSE_500},
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
        summary="Детали курса",
        description=(
            "Возвращает полную информацию о курсе по slug. Доступно всем авторизованным пользователям. "
            "Права доступа: Студент - просмотр, Учитель - просмотр, Модератор - просмотр."
        ),
        tags=["Courses"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug курса'
            ),
        ],
        responses={
            200: CourseSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Курс не найден.", "schema": SCHEMA_COURSE_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_COURSE_500},
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
        description=(
            "Обновляет курс. Модераторы могут обновлять любые курсы, учителя - только свои. "
            "Права доступа: Студент - запрещено, Учитель - только свои курсы (где он в authors), Модератор - все курсы."
        ),
        tags=["Courses"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug курса'
            ),
        ],
        responses={
            200: CourseSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен. Требуется быть автором курса.", "schema": SCHEMA_403},
            404: {"description": "Курс не найден.", "schema": SCHEMA_COURSE_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_COURSE_500},
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
        description=(
            "Удаляет курс. Модераторы могут удалять любые курсы, учителя - только свои. "
            "Права доступа: Студент - запрещено, Учитель - только свои курсы (где он в authors), Модератор - все курсы."
        ),
        tags=["Courses"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug курса'
            ),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен. Требуется быть автором курса.", "schema": SCHEMA_403},
            404: {"description": "Курс не найден.", "schema": SCHEMA_COURSE_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_COURSE_500},
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
        summary="Купленные курсы",
        description=(
            "Возвращает список купленных курсов текущего пользователя с датой окончания доступа. "
            "Требуется Authorization: Bearer <access_token>. "
            "Каждый элемент: id, course (DTO курса), payment (id платежа), access_expires_at, is_active (доступ активен или истёк). "
            "При невалидном токене — 401 с полем detail."
        ),
        tags=["My Courses"],
        responses={
            200: PurchasedCourseSerializer(many=True),
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
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
        summary="Главная страница курса",
        description=(
            "Возвращает данные курса с секциями и уроками. "
            "Для подписанных пользователей — без поля type. "
            "Для авторов и модераторов — с полем type у секций и уроков. "
            "Для остальных — 403 Forbidden."
        ),
        tags=["Courses"],
        parameters=[
            OpenApiParameter(
                name='course_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug курса'
            ),
        ],
        responses={
            200: CourseHomePageSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Курс не найден.", "schema": SCHEMA_COURSE_404},
        }
    )
    def get(self, request, course_slug):
        try:
            course = Course.objects.get(slug=course_slug)
        except Course.DoesNotExist:
            return Response(
                {'detail': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

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

        serializer = CourseHomePageSerializer(
            course,
            context={'is_author': show_type}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


def _lesson_queryset_for_course(course_slug):
    return Lesson.objects.filter(section__course__slug=course_slug)


def _get_lesson_or_404(course_slug, lesson_slug):
    return get_object_or_404(_lesson_queryset_for_course(course_slug), slug=lesson_slug)


def _homework_queryset_for_lesson(course_slug, lesson_slug):
    return Homework.objects.filter(
        lesson__slug=lesson_slug,
        lesson__section__course__slug=course_slug,
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
        tags=["Sections"],
        request=SectionSerializer,
        responses={
            201: SectionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
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
        tags=["Sections"],
        parameters=[
            OpenApiParameter(
                name='section_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug секции',
            ),
        ],
        request=SectionSerializer,
        responses={
            200: SectionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Секция не найдена.", "schema": SCHEMA_SECTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
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
        tags=["Sections"],
        parameters=[
            OpenApiParameter(
                name='section_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug секции',
            ),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Секция не найдена.", "schema": SCHEMA_SECTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
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
        summary="Создать новый урок",
        tags=["Lessons"],
        request=LessonSerializer,
        responses={
            201: LessonSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
        }
    )
    @require_course_author
    def post(self, request, course_slug):
        serializer = LessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LessonDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LessonSerializer

    @extend_schema(
        summary="Получить информацию о уроке",
        tags=["Lessons"],
        parameters=[
            OpenApiParameter(
                name='lesson_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug урока'),
        ],
        responses={
            200: LessonSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Урок не найден.", "schema": SCHEMA_LESSON_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
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
        data = LessonSerializer(lesson).data
        cache.set(key, data)
        return Response(data)

    @extend_schema(
        summary="Обновить урок",
        tags=["Lessons"],
        parameters=[
            OpenApiParameter(
                name='lesson_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug урока'),
        ],
        request=LessonSerializer,
        responses={
            200: LessonSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Урок не найден.", "schema": SCHEMA_LESSON_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
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
        tags=["Lessons"],
        parameters=[
            OpenApiParameter(
                name='lesson_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug урока'),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Урок не найден.", "schema": SCHEMA_LESSON_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
        }
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug):
        lesson = _get_lesson_or_404(course_slug, lesson_slug)
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HomeworkListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Получить список домашних заданий",
        tags=["Homeworks"],
        responses={
            200: HomeworkSerializer(many=True),
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
        }
    )
    @require_course_enrollment
    def get(self, request, course_slug, lesson_slug):
        cache = caches["default"]
        key = homework_list_cache_key(course_slug, lesson_slug)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        qs = _homework_queryset_for_lesson(course_slug, lesson_slug)
        data = HomeworkSerializer(qs, many=True).data
        cache.set(key, data)
        return Response(data)

    @extend_schema(
        summary="Создать домашнее задание",
        description="Создаёт домашнее задание вместе с вопросами и задачами.",
        tags=["Homeworks"],
        request=HomeworkCreateSerializer,
        responses={
            201: HomeworkSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
        }
    )
    @require_course_author
    def post(self, request, course_slug, lesson_slug):
        serializer = HomeworkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        homework = serializer.save()
        response_serializer = HomeworkSerializer(homework)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class HomeworkDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Получить домашнее задание",
        description="Возвращает домашнее задание с задачами и вопросами",
        tags=["Homeworks"],
        parameters=[
            OpenApiParameter(
                name='homework_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug домашнего задания'),
        ],
        responses={
            200: HomeworkSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Домашнее задание не найдено.", "schema": SCHEMA_HOMEWORK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        data = HomeworkSerializer(homework).data
        cache.set(key, data)
        return Response(data)

    @extend_schema(
        summary="Обновить домашнее задание",
        description="Обновляет домашнее задание.",
        tags=["Homeworks"],
        parameters=[
            OpenApiParameter(
                name='homework_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug домашнего задания'),
        ],
        request=HomeworkCreateSerializer,
        responses={
            200: HomeworkSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Домашнее задание не найдено.", "schema": SCHEMA_HOMEWORK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
        }
    )
    @require_course_author
    def patch(self, request, course_slug, lesson_slug, homework_slug):
        homework = _get_homework_or_404(course_slug, lesson_slug, homework_slug)
        serializer = HomeworkCreateSerializer(homework, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        homework = serializer.save()
        response_serializer = HomeworkSerializer(homework)
        return Response(response_serializer.data)

    @extend_schema(
        summary="Удалить домашнее задание",
        tags=["Homeworks"],
        parameters=[
            OpenApiParameter(
                name='homework_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug домашнего задания'),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Домашнее задание не найдено.", "schema": SCHEMA_HOMEWORK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        summary="Создать задачу в домашнем задании",
        tags=["Tasks"],
        request=TaskSerializer,
        responses={
            201: TaskSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Домашнее задание не найдено.", "schema": SCHEMA_HOMEWORK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        tags=["Tasks"],
        parameters=[
            OpenApiParameter(
                name='task_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='id задачи',
            ),
        ],
        request=TaskSerializer,
        responses={
            200: TaskSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Задача не найдена.", "schema": SCHEMA_TASK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        tags=["Tasks"],
        parameters=[
            OpenApiParameter(
                name='task_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='id задачи',
            ),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Задача не найдена.", "schema": SCHEMA_TASK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        summary="Создать вопрос в домашнем задании",
        tags=["Questions"],
        request=QuestionSerializer,
        responses={
            201: QuestionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Домашнее задание не найдено.", "schema": SCHEMA_HOMEWORK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        tags=["Questions"],
        parameters=[
            OpenApiParameter(
                name='question_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='id вопроса',
            ),
        ],
        request=QuestionSerializer,
        responses={
            200: QuestionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Вопрос не найден.", "schema": SCHEMA_QUESTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
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
        tags=["Questions"],
        parameters=[
            OpenApiParameter(
                name='question_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='id вопроса',
            ),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            403: {"description": "Доступ запрещен.", "schema": SCHEMA_403},
            404: {"description": "Вопрос не найден.", "schema": SCHEMA_QUESTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
        }
    )
    @require_course_author
    def delete(self, request, course_slug, lesson_slug, homework_slug, question_id):
        question = _get_question_or_404(course_slug, lesson_slug, homework_slug, question_id)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
