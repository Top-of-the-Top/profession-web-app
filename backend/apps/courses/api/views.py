from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.http import Http404
from rest_framework.exceptions import NotFound
from ..models import Course
from .serializers import CourseDTOSerializer, CourseSerializer
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

SCHEMA_401 = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "string",
            "description": "Сообщение об ошибке аутентификации (например: учётные данные не переданы или токен недействителен).",
            "example": "Authentication credentials were not provided.",
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
        description="Публичный список курсов в формате DTO для лендинга. Без авторизации.",
        responses={200: CourseDTOSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CourseDTOListAuthenticated(CourseDTOListBase):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Список курсов (store)",
        description="Список курсов в формате DTO для магазина приложения. Только для авторизованных пользователей.",
        responses={
            200: CourseDTOSerializer(many=True),
            401: {
                "description": "Не авторизован. Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CourseDetail(RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_url_kwarg = 'slug'
    lookup_field = 'slug'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound(detail="Курс не найден")

    @extend_schema(
        summary="Детали курса",
        description="Полная информация о курсе по slug",
        tags=["Courses"],
        responses={
            200: CourseSerializer,
            401: {
                "description": "Не авторизован. Токен отсутствует или недействителен.",
                "schema": SCHEMA_401,
            },
            404: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, *args, **kwargs):
        course = self.get_object()
        serializer = self.get_serializer(course)
        data = serializer.data

        return Response({'course': data})
