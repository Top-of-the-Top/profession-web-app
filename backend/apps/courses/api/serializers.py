from .models import Course
from rest_framework import serializers


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = '__all__'

class CourseDTOSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = Course
        fields = ['course_id', 'title', 'sub_title', 'image_url', 'price', 'slug']