from django.contrib.admin import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.views import APIView
from ..models import Course, PurchasedCourse, Lesson, Task, Homework, Question
from .serializers import (
    CourseDTOSerializer,
    CourseSerializer,
    CourseListResponseSerializer,
    CourseDetailResponseSerializer,
    PurchasedCourseSerializer,
    LessonSerializer,
    HomeworkSerializer,
    QuestionSerializer,
    TaskSerializer
)
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


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


class CourseDTOListBase(generics.ListAPIView):
    serializer_class = CourseDTOSerializer


    def get_queryset(self):
        return Course.objects.all()


    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'number_of_courses': len(serializer.data),
            'data': serializer.data,
        })



class CourseDTOList(CourseDTOListBase):
    permission_classes = (AllowAny,)


    @extend_schema(
        summary="Список курсов (лендинг)",
        description=(
            "Публичный список всех курсов для лендинга. Авторизация не требуется. "
            "Возвращается объект: number_of_courses (число курсов) и data — массив курсов в формате DTO (course_id, title, sub_title, image_url, price, slug)."
        ),
        tags=["Courses"],
        responses={200: CourseListResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)



class CourseDTOListAuthenticated(CourseDTOListBase):
    permission_classes = (IsAuthenticated,)


    @extend_schema(
        summary="Список курсов (store)",
        description=(
            "Список всех курсов для магазина приложения. Требуется Authorization: Bearer <access_token>. "
            "Формат ответа тот же, что и у списка для лендинга: number_of_courses и data (массив курсов: course_id, title, sub_title, image_url, price, slug). "
            "При невалидном токене — 401 с полем detail."
        ),
        tags=["Courses"],
        responses={
            200: CourseListResponseSerializer,
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)



class CourseDetail(RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_url_kwarg = 'slug'
    lookup_field = 'slug'


    @extend_schema(
        summary="Детали курса",
        description=(
            "Возвращает полную информацию о курсе по slug (в пути URL). Требуется Authorization: Bearer <access_token>. "
            "В ответе объект с единственным полем course — полная модель курса (все поля из БД плюс вычисляемое image_url). "
            "Если курс с указанным slug не найден — 404 с полем detail: «Курс не найден». "
            "При невалидном токене — 401."
        ),
        tags=["Courses"],
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug курса'),
        ],
        responses={
            200: CourseDetailResponseSerializer,
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
            404: {"description": "Тело: { detail: 'Курс не найден' }.", "schema": SCHEMA_COURSE_404},
        },
    )
    def get(self, request, *args, **kwargs):
        course = Course.objects.filter(slug=kwargs.get('slug')).first()
        if course is None:
            return Response(
                {'detail': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(course)
        return Response({'course': serializer.data})



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
        tags=["Courses"],
        responses={
            200: PurchasedCourseSerializer(many=True),
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def get(self, request):
        purchased = PurchasedCourse.objects.filter(
            user=request.user,
        ).select_related('course', 'payment')


        serializer = PurchasedCourseSerializer(purchased, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LessonViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
       course_slug = self.kwargs['course_slug']
       return Lesson.objects.filter(course__slug=course_slug)

    @extend_schema(
      summary="Получить список уроков",
      tags=["Lessons"],
      responses={
        200: LessonSerializer(many=True),
        401: {"description": "Не авторизован", "schema": SCHEMA_401},
        500: {"description": "Внутренняя ошибка сервера.", "schema": SCHEMA_LESSON_500},
      }
    )
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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class HomeworkViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        lesson_slug = self.kwargs['lesson_slug']
        return Homework.objects.filter(
            lesson__slug=lesson_slug, 
            lesson__course__slug=course_slug
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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        lesson_slug = self.kwargs['lesson_slug']
        homework_slug = self.kwargs['homework_slug']
        return Task.objects.filter(
            homework__slug=homework_slug,
            homework__lesson__slug=lesson_slug, 
            homework__lesson__course__slug=course_slug
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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_field = 'slug'

    def get_queryset(self):
        course_slug = self.kwargs['course_slug']
        lesson_slug = self.kwargs['lesson_slug']
        homework_slug = self.kwargs['homework_slug']
      
        return Question.objects.filter(
            homework__slug=homework_slug,
            homework__lesson__slug=lesson_slug, 
            homework__lesson__course__slug=course_slug
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
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
