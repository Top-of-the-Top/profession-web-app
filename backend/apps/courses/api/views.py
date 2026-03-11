from django.contrib.admin import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.views import APIView
from ..models import Course, PurchasedCourse
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
SCHEMA_404 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Курс не найден.",
            "example": "Курс не найден",
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
            404: {"description": "Тело: { detail: 'Курс не найден' }.", "schema": SCHEMA_404},
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

    @extend_schema(
      description="Получить список уроков",
      tags=["Lessons"],
      responses={
        200: LessonSerializer(many=True),
        401: 'Не авторизован'
      }
    )
    def list(self, request, *args, **kwargs):
      pass

    @extend_schema(
      description="Создать новый урок",
      tags=["Lessons"],
      responses={
        201: LessonSerializer(many=True),
        401: 'Не авторизован'
      }
    )
    def create(self, request, *args, **kwargs):
      pass

    @extend_schema(
      description="Получить информацию о уроке",
      tags=["Lessons"],
      responses={
        200: LessonSerializer(many=True),
        401: 'Не авторизован'
      }
    )
    def retrieve(self, request, *args, **kwargs):
      pass

    @extend_schema(
      description="Обновить урок",
      tags=["Lessons"],
      responses={
        200: LessonSerializer(many=True),
        401: 'Не авторизован'
      }
    )

    def partial_update(self, request, *args, **kwargs):
      pass


    @extend_schema(
      description="Удалить урок",
      tags=["Lessons"],
      responses={
        204: LessonSerializer(many=True),
        401: 'Не авторизован'
      }
    )

    def destroy(self, request, *args, **kwargs):
      pass


class HomeworkViewSet(viewsets.ModelViewSet):
  permission_classes = (IsAuthenticated,)
  http_method_names = ['get', 'post', 'patch', 'delete']
  lookup_field = 'slug'

  @extend_schema(
    description="Получить список домашних заданий",
    tags=["Homeworks"],
    responses={
      200: HomeworkSerializer(many=True),
      401: 'Не авторизован'
    }
  )
  def list(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Создать новое домашнее задание",
    tags=["Homeworks"],
    responses={
      201: HomeworkSerializer(many=True),
      401: 'Не авторизован'
    }
  )
  def create(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Получить информацию о домашнем задании",
    tags=["Homeworks"],
    responses={
      200: HomeworkSerializer(many=True),
      401: 'Не авторизован'
    }
  )
  def retrieve(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Обновить домашнее задание",
    tags=["Homeworks"],
    responses={
      200: HomeworkSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def partial_update(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Удалить домашнее задание",
    tags=["Homeworks"],
    responses={
      204: HomeworkSerializer(many=True),
      401: 'Не авторизован'
    }
  )
  def destroy(self, request, *args, **kwargs):
    pass

class TaskViewSet(viewsets.ModelViewSet):
  permission_classes = (IsAuthenticated,)
  http_method_names = ['get', 'post', 'patch', 'delete']

  @extend_schema(
    description="Получить список задач",
    tags=["Tasks"],
    responses={
      200: TaskSerializer(many=True),
      401: 'Не авторизован'
    }
  )
  def list(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Создать задачу ",
    tags=["Tasks"],
    responses={
      201: TaskSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def create(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Получить информацию о задаче",
    tags=["Tasks"],
    responses={
      200: TaskSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def retrieve(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Обновить задачу",
    tags=["Tasks"],
    responses={
      200: TaskSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def partial_update(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Удалить задачу",
    tags=["Tasks"],
    responses={
      204: TaskSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def destroy(self, request, *args, **kwargs):
    pass


class QuestionViewSet(viewsets.ModelViewSet):
  permission_classes = (IsAuthenticated,)
  http_method_names = ['get', 'post', 'patch', 'delete']

  @extend_schema(
    description="Получить список вопросов",
    tags=["Questions"],
    responses={
      200: QuestionSerializer(many=True),
      401: 'Не авторизован'
    }
  )
  def list(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Создать вопрос",
    tags=["Questions"],
    responses={
      201: QuestionSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def create(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Получить информацию о вопросе",
    tags=["Questions"],
    responses={
      200: QuestionSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def retrieve(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Обновить вопрос",
    tags=["Questions"],
    responses={
      200: QuestionSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def partial_update(self, request, *args, **kwargs):
    pass

  @extend_schema(
    description="Удалить вопрос",
    tags=["Questions"],
    responses={
      204: QuestionSerializer(many=True),
      401: 'Не авторизован'
    }
  )

  def destroy(self, request, *args, **kwargs):
    pass
