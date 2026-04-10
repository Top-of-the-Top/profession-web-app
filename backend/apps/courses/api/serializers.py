from ..models import (
    Course,
    PurchasedCourse,
    Lesson,
    Homework,
    Section,
    Question,
    Task,
)
from django.db.models import Prefetch

from apps.users.models import User
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()
    authors = serializers.PrimaryKeyRelatedField(
        many=True, read_only=False, required=False, queryset=User.objects.all()
    )

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('course_id', 'created_at', 'updated_at', 'last_modified_by')


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
            'slug',
        ]


class CourseListResponseSerializer(serializers.Serializer):
    number_of_courses = serializers.IntegerField()
    data = CourseDTOSerializer(many=True, read_only=True)


class PurchasedCourseSerializer(serializers.ModelSerializer):
    course = CourseDTOSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = PurchasedCourse
        fields = ('id', 'user', 'course', 'payment', 'access_expires_at', 'is_active')


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'
        read_only_fields = (
            'section_id',
            'created_at',
            'updated_at',
            'last_modified_by',
        )


class LessonBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['lesson_id', 'lesson_number', 'title', 'slug']


class LessonBriefWithTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['lesson_id', 'lesson_number', 'title', 'slug', 'type']


class SectionWithLessonsSerializer(serializers.ModelSerializer):
    lessons = LessonBriefSerializer(many=True, read_only=True, source='lesson_set')

    class Meta:
        model = Section
        fields = ['section_id', 'section_number', 'title', 'lessons']


class SectionWithLessonsAndTypeSerializer(serializers.ModelSerializer):
    lessons = LessonBriefWithTypeSerializer(many=True, read_only=True, source='lesson_set')

    class Meta:
        model = Section
        fields = ['section_id', 'section_number', 'title', 'type', 'lessons']


class CourseHomeSerializer(serializers.Serializer):
    course_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    content = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()

    @extend_schema_field(SectionWithLessonsAndTypeSerializer(many=True))
    def get_content(self, obj):
        lesson_qs = Lesson.objects.order_by('lesson_number')
        sections = (
            Section.objects.filter(course=obj)
            .order_by('section_number')
            .prefetch_related(Prefetch('lesson_set', queryset=lesson_qs))
        )
        is_author = self.context.get('is_author', False)

        if is_author:
            return SectionWithLessonsAndTypeSerializer(sections, many=True).data
        return SectionWithLessonsSerializer(sections, many=True).data

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_meta(self, obj):
        return {}


class HomeworkBriefSerializer(serializers.Serializer):
    homework_id = serializers.UUIDField()
    title = serializers.CharField(max_length=120)
    homework_slug = serializers.SlugField()
    deadline = serializers.DateTimeField()


class LessonContentReadSerializer(serializers.Serializer):
    recording_url = serializers.URLField()
    started_at = serializers.DateTimeField()
    homeworks = HomeworkBriefSerializer(many=True)


class LessonDetailReadSerializer(serializers.ModelSerializer):
    lesson_id = serializers.UUIDField(read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ('lesson_id', 'title', 'content')

    @extend_schema_field(LessonContentReadSerializer)
    def get_content(self, obj):
        return {
            'recording_url': 'https://example.com/recordings/mock-lesson',
            'started_at': '2026-01-15T10:00:00+00:00',
            'homeworks': [
                {
                    'homework_id': h.homework_id,
                    'title': h.title,
                    'homework_slug': h.slug,
                    'deadline': h.deadline,
                }
                for h in obj.homework_set.all()
            ],
        }


class LessonSerializer(serializers.ModelSerializer):
    section = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = (
            'lesson_id',
            'created_at',
            'updated_at',
            'last_modified_by',
        )


class HomeworkItemsListSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['question', 'task'])
    id = serializers.UUIDField(required=False, allow_null=True)
    number = serializers.IntegerField(read_only=True)
    text = serializers.CharField(max_length=200)
    answer_options = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    correct_ans = serializers.CharField(required=False, allow_null=True)
    max_points = serializers.IntegerField(required=False, allow_null=True, default=0)
    created_at = serializers.DateTimeField(read_only=True)


class HomeworkDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    lesson_id = serializers.UUIDField(source='lesson.lesson_id', read_only=True)

    class Meta:
        model = Homework
        fields = [
            'homework_id',
            'homework_number',
            'lesson_id',
            'title',
            'slug',
            'deadline',
            'type',
            'created_at',
            'updated_at',
            'items',
        ]
        read_only_fields = (
            'homework_id',
            'created_at',
            'updated_at',
            'last_modified_by',
        )

    @extend_schema_field(HomeworkItemsListSerializer(many=True))
    def get_items(self, obj):
        questions = list(obj.question_set.all())
        tasks = list(obj.task_set.all())

        items = []
        for q in questions:
            items.append({
                'type': 'question',
                'id': q.question_id,
                'number': q.question_number,
                'text': q.text,
                'answer_options': q.answer_options,
                'correct_ans': q.correct_ans,
                'max_points': None,
                'created_at': q.created_at,
            })
        for t in tasks:
            items.append({
                'type': 'task',
                'id': t.task_id,
                'number': t.task_number,
                'text': t.text,
                'answer_options': None,
                'correct_ans': None,
                'max_points': t.max_points,
                'created_at': t.created_at,
            })

        items.sort(key=lambda x: (x['number'], x['created_at']))
        return items


class HomeworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = '__all__'
        read_only_fields = (
            'homework_id',
            'created_at',
            'updated_at',
            'last_modified_by',
        )


class TaskSerializer(serializers.ModelSerializer):
    homework = serializers.PrimaryKeyRelatedField(
        queryset=Homework.objects.all(), required=False
    )

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = (
            'task_id',
            'created_at',
            'updated_at',
            'last_modified_by',
        )


class QuestionSerializer(serializers.ModelSerializer):
    homework = serializers.PrimaryKeyRelatedField(
        queryset=Homework.objects.all(), required=False
    )

    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = (
            'question_id',
            'created_at',
            'updated_at',
            'last_modified_by',
        )
