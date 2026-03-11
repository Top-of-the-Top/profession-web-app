from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from ..models import Course, PurchasedCourse
from .serializers import (
    CourseDTOSerializer,
    CourseSerializer,
    CourseListResponseSerializer,
    CourseDetailResponseSerializer,
    PurchasedCourseSerializer,
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
