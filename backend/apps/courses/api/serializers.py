from ..models import Course, PurchasedCourse
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


class PurchasedCourseSerializer(serializers.ModelSerializer):
    course = CourseDTOSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = PurchasedCourse
        fields = [
            'id',
            'course',
            'payment',
            'access_expires_at',
            'is_active',
        ]