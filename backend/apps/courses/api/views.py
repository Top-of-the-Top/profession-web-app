from django.http import Http404
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models import Course
from .serializers import CourseDTOSerializer, CourseSerializer
from rest_framework import generics


class CourseDTOList(generics.ListAPIView):
    serializer_class = CourseDTOSerializer
    
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
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = 'slug' # Поле для поиска объекта

    def get(self, request, *args, **kwargs):
        course = self.get_object()
        serializer = self.get_serializer(course)
        data = serializer.data

        return Response({'course': data})
