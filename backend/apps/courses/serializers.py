from .models import Course
from rest_framework import serializers


class CourseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = ['title', 'price', 'image']