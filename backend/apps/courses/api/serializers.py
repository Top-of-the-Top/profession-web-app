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
        fields = [
            'course_id',
            'title',
            'sub_title',
            'image_url',
            'price',
            'slug']


class CourseListResponseSerializer(serializers.Serializer):
    """Обёртка ответа списка курсов (лендинг / store)."""
    number_of_courses = serializers.IntegerField()
    data = CourseDTOSerializer(many=True, read_only=True)


class CourseDetailResponseSerializer(serializers.Serializer):
    """Обёртка ответа деталей курса: одно поле course."""
    course = CourseSerializer(read_only=True)


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
