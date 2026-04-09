from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework.views import APIView
from ..models import Course, PurchasedCourse, Lesson, Task, Homework, Question, Section
from .serializers import (
    CourseDTOSerializer,
    CourseSerializer,
    PurchasedCourseSerializer,
    CourseListResponseSerializer,
    LessonSerializer,
    HomeworkSerializer,
    QuestionSerializer,
    TaskSerializer,
    CourseHomePageSerializer,
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
SCHEMA_TASK_500 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Внутренняя ошибка сервера.",
            "example": "Произошла ошибка при обработке запроса.",
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
SCHEMA_QUESTION_500 = {
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

def task_list_cache_key(course_slug, lesson_slug, homework_slug):
    return f"default:tasks:list:{course_slug}:{lesson_slug}:{homework_slug}"

def task_detail_cache_key(course_slug, lesson_slug, homework_slug, slug):
    return f"default:tasks:detail:{course_slug}:{lesson_slug}:{homework_slug}:{slug}"

def question_list_cache_key(course_slug, lesson_slug, homework_slug):
    return f"default:questions:list:{course_slug}:{lesson_slug}:{homework_slug}"

def question_detail_cache_key(course_slug, lesson_slug, homework_slug, slug):
    return f"default:questions:detail:{course_slug}:{lesson_slug}:{homework_slug}:{slug}"

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


class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseSerializer
    queryset = Course.objects.all()
    lookup_field = 'slug'
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return Course.objects.all()

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
    def list(self, request, *args, **kwargs):
        cache = caches["default"]
        key = course_list_cache_key()
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

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
    def retrieve(self, request, *args, **kwargs):
        cache = caches["default"]
        key = course_detail_cache_key(self.kwargs.get("slug", ""))
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

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
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

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
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


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


class LessonViewSet(
    CreateModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    serializer_class = LessonSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs.get('course_slug')
        if course_slug:
            return Lesson.objects.filter(section__course__slug=course_slug)
        return Lesson.objects.all()


    @extend_schema(
        summary="Создать новый урок",
        tags=["Lessons"],
        responses={
            201: LessonSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
        }
    )
    @require_course_author
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить информацию о уроке",
        tags=["Lessons"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
    def retrieve(self, request, *args, **kwargs):
        cache = caches["default"]
        key = lesson_detail_cache_key(
            self.kwargs['course_slug'], self.kwargs.get("slug", "")
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Обновить урок",
        tags=["Lessons"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
    @require_course_author
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить урок",
        tags=["Lessons"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class HomeworkViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = HomeworkSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        lesson_slug = self.kwargs['lesson_slug']
        return Homework.objects.filter(
            lesson__slug=lesson_slug,
            lesson__section__course__slug=course_slug
        )

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
    def list(self, request, *args, **kwargs):
        cache = caches["default"]
        key = homework_list_cache_key(
            self.kwargs['course_slug'], self.kwargs['lesson_slug']
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Создать новое домашнее задание",
        tags=["Homeworks"],
        responses={
            201: HomeworkSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_HOMEWORK_500},
        }
    )
    @require_course_author
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить информацию о домашнем задании",
        tags=["Homeworks"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
    def retrieve(self, request, *args, **kwargs):
        cache = caches["default"]
        key = homework_detail_cache_key(
            self.kwargs['course_slug'], self.kwargs['lesson_slug'], self.kwargs.get("slug", "")
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Обновить домашнее задание",
        tags=["Homeworks"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
    @require_course_author
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить домашнее задание",
        tags=["Homeworks"],
        parameters=[
            OpenApiParameter(
                name='slug',
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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        lesson_slug = self.kwargs['lesson_slug']
        homework_slug = self.kwargs['homework_slug']
        return Task.objects.filter(
            homework__slug=homework_slug,
            homework__lesson__slug=lesson_slug,
            homework__lesson__section__course__slug=course_slug
        )

    @extend_schema(
        summary="Получить список задач",
        tags=["Tasks"],
        responses={
            200: TaskSerializer(many=True),
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_TASK_500},
        }
    )
    @require_course_enrollment
    def list(self, request, *args, **kwargs):
        cache = caches["default"]
        key = task_list_cache_key(
            self.kwargs['course_slug'], self.kwargs['lesson_slug'], self.kwargs['homework_slug']
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Создать задачу ",
        tags=["Tasks"],
        responses={
            201: TaskSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_TASK_500},
        }
    )
    @require_course_author
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить информацию о задаче",
        tags=["Tasks"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug задачи'),
        ],
        responses={
            200: TaskSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Задача не найдена.", "schema": SCHEMA_TASK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_TASK_500},
        }
    )
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        cache = caches["default"]
        key = task_detail_cache_key(
            self.kwargs['course_slug'], self.kwargs['lesson_slug'],
            self.kwargs['homework_slug'], self.kwargs.get("slug", "")
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Обновить задачу",
        tags=["Tasks"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug задачи'),
        ],
        responses={
            200: TaskSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Задача не найдена.", "schema": SCHEMA_TASK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_TASK_500},
        }
    )
    @require_course_author
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить задачу",
        tags=["Tasks"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug задачи'),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Задача не найдена.", "schema": SCHEMA_TASK_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_TASK_500},
        }
    )
    @require_course_author
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = QuestionSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        lesson_slug = self.kwargs['lesson_slug']
        homework_slug = self.kwargs['homework_slug']
        return Question.objects.filter(
            homework__slug=homework_slug,
            homework__lesson__slug=lesson_slug,
            homework__lesson__section__course__slug=course_slug
        )

    @extend_schema(
        summary="Получить список вопросов",
        tags=["Questions"],
        responses={
            200: QuestionSerializer(many=True),
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_QUESTION_500},
        }
    )
    @require_course_enrollment
    def list(self, request, *args, **kwargs):
        cache = caches["default"]
        key = question_list_cache_key(
            self.kwargs['course_slug'], self.kwargs['lesson_slug'], self.kwargs['homework_slug']
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Создать вопрос",
        tags=["Questions"],
        responses={
            201: QuestionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_QUESTION_500},
        }
    )
    @require_course_author
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить информацию о вопросе",
        tags=["Questions"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug вопроса'),
        ],
        responses={
            200: QuestionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Вопрос не найден.", "schema": SCHEMA_QUESTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_QUESTION_500},
        }
    )
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        cache = caches["default"]
        key = question_detail_cache_key(
            self.kwargs['course_slug'], self.kwargs['lesson_slug'],
            self.kwargs['homework_slug'], self.kwargs.get("slug", "")
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        cache.set(key, response.data)
        return response

    @extend_schema(
        summary="Обновить вопрос",
        tags=["Questions"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug вопроса'),
        ],
        responses={
            200: QuestionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Вопрос не найден.", "schema": SCHEMA_QUESTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_QUESTION_500},
        }
    )
    @require_course_author
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить вопрос",
        tags=["Questions"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug вопроса'),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Вопрос не найден.", "schema": SCHEMA_QUESTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_QUESTION_500},
        }
    )
    @require_course_author
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
