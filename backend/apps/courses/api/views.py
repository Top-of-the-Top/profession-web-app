from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import Http404
from rest_framework.exceptions import NotFound
from ..models import Course
from .serializers import CourseDTOSerializer, CourseSerializer
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

class CourseDTOList(generics.ListAPIView):
    serializer_class = CourseDTOSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Course.objects.all()
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'number_of_courses': len(serializer.data),
            'data': serializer.data
        })

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
        parameters=[
            OpenApiParameter(
                name='slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='slug курса',
            )
        ],
        responses={
            200: CourseSerializer,
            404: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request, *args, **kwargs):
        course = self.get_object()
        serializer = self.get_serializer(course)
        data = serializer.data

        return Response({'course': data})
