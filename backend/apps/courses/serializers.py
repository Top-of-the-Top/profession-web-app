from .models import Course
from rest_framework import serializers


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = ['course_id', 'title', 'price', 'image_url']