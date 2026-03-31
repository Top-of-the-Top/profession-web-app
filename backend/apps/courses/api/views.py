from django.contrib.admin import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
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
    SectionSerializer
)
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.users.api.decorators import require_moderator, require_course_author, require_course_enrollment
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
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

class CourseDTOList(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = CourseDTOSerializer

    def get_queryset(self):
        user = self.request.user
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
    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'number_of_courses': len(serializer.data),
            'data': serializer.data,
        })

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
    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    @method_decorator(cache_page(60 * 10))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        purchased = PurchasedCourse.objects.filter(
            user=request.user,
        ).select_related('course', 'payment')


        serializer = PurchasedCourseSerializer(purchased, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SectionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    serializer_class = SectionSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        return Section.objects.filter(course__slug=course_slug)

    @extend_schema(
        summary="Получить список секций курса",
        tags=["Sections"],
        responses={
            200: SectionSerializer(many=True),
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
        }
    )
    @require_course_enrollment
    @method_decorator(cache_page(60 * 60))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Создать новую секцию",
        tags=["Sections"],
        responses={
            201: SectionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
        }
    )
    @require_course_author
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить информацию о секции",
        tags=["Sections"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug секции'),
        ],
        responses={
            200: SectionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Секция не найдена.", "schema": SCHEMA_SECTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
        }
    )
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Обновить секцию",
        tags=["Sections"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug секции'),
        ],
        responses={
            200: SectionSerializer,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Секция не найдена.", "schema": SCHEMA_SECTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
        }
    )
    @require_course_author
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить секцию",
        tags=["Sections"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug секции'),
        ],
        responses={
            204: None,
            401: {"description": "Не авторизован", "schema": SCHEMA_401},
            404: {"description": "Секция не найдена.", "schema": SCHEMA_SECTION_404},
            500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_SECTION_500},
        }
    )
    @require_course_author
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class LessonViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    serializer_class = LessonSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        section_slug = self.kwargs.get('section_slug')
        if section_slug:
            return Lesson.objects.filter(section_id__slug=section_slug)
        return Lesson.objects.all()

    @extend_schema(
      summary="Получить список уроков",
      tags=["Lessons"],
      responses={
        200: LessonSerializer(many=True),
        401: {"description": "Не авторизован", "schema": SCHEMA_401},
        500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
      }
    )
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
        section_slug = self.kwargs['section_slug']
        lesson_slug = self.kwargs['lesson_slug']
        return Homework.objects.filter(
            lesson__slug=lesson_slug,
            lesson__section__slug=section_slug,
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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
        section_slug = self.kwargs['section_slug']
        lesson_slug = self.kwargs['lesson_slug']
        homework_slug = self.kwargs['homework_slug']
        return Task.objects.filter(
            homework__slug=homework_slug,
            homework__lesson__slug=lesson_slug,
            homework__lesson__section__slug=section_slug,
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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
        section_slug = self.kwargs['section_slug']
        lesson_slug = self.kwargs['lesson_slug']
        homework_slug = self.kwargs['homework_slug']

        return Question.objects.filter(
            homework__slug=homework_slug,
            homework__lesson__slug=lesson_slug,
            homework__lesson__section__slug=section_slug,
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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    @method_decorator(cache_page(60 * 10))
    @require_course_enrollment
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

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
