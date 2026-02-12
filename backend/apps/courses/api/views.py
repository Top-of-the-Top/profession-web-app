
from rest_framework.response import Response


from ..models import Course
from .serializers import CourseDTOSerializer
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
