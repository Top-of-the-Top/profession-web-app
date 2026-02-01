
from rest_framework.response import Response


from .models import Course
from .serializers import CourseSerializer
from rest_framework import viewsets, status, generics


class CourseList(generics.ListAPIView):
    serializer_class = CourseSerializer
    def get_queryset(self):
        queryset = Course.objects.all()
        return queryset[:6]
