from ..models import Course, PurchasedCourse, Lesson, Homework, Section, Question, Task
from apps.users.models import User
from rest_framework import serializers


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()
    authors = serializers.PrimaryKeyRelatedField(many=True, read_only=False, required=False, queryset=User.objects.all())

    class Meta:
        model = Course
        fields = '__all__'
        extra_kwargs = {
            'course_id': {'read_only': True},
            'slug': {'required': False},
            'image': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'last_modified_by': {'required': False},
        }


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

class SectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Section
        fields = '__all__'
        extra_kwargs = {
            'section_id': {'read_only': True, 'required': False},
            'slug': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'last_modified_by': {'required': False},
        }

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        extra_kwargs = {
            'lesson_id': {'read_only': True},
            'section_id': {'required': False, 'allow_null': True},
            'slug': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'last_modified_by': {'required': False},
        }

class HomeworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = '__all__'
        extra_kwargs = {
            'homework_id': {'read_only': True},
            'slug': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'last_modified_by': {'required': False},
        }

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        extra_kwargs = {
            'question_id': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'last_modified_by': {'required': False},
        }

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        extra_kwargs = {
            'task_id': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'last_modified_by': {'required': False},
        }
