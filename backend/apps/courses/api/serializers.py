from .utils.rbac_utils import filter_homework_queryset_for_visibility
import json

from ..models import (
    Course,
    PurchasedCourse,
    Lesson,
    Homework,
    Section,
    Question,
    Task,
    Webinar,
    PublishableMixin,
)
from ..lesson_content import resolve_lesson_document_string
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
        fields = ['section_id', 'section_number', 'title', 'lessons', 'slug']


class SectionWithLessonsAndTypeSerializer(serializers.ModelSerializer):
    lessons = LessonBriefWithTypeSerializer(many=True, read_only=True, source='lesson_set')

    class Meta:
        model = Section
        fields = ['section_id', 'section_number', 'title', 'type', 'lessons', 'slug']


class CourseHomeSerializer(serializers.Serializer):
    course_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    content = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()

    @extend_schema_field(SectionWithLessonsAndTypeSerializer(many=True))
    def get_content(self, obj):
        is_author = self.context.get('is_author', False)

        if is_author:
            lesson_qs = Lesson.objects.order_by('lesson_number')
            sections = (
                Section.objects.filter(course=obj)
                .order_by('section_number')
                .prefetch_related(Prefetch('lesson_set', queryset=lesson_qs))
            )
            return SectionWithLessonsAndTypeSerializer(sections, many=True).data

        if obj.type != Course.PUBLISHED_STATUS:
            return []

        lesson_qs = Lesson.objects.filter(type=Lesson.PUBLISHED_STATUS).order_by('lesson_number')
        sections = (
            Section.objects.filter(course=obj, type=Section.PUBLISHED_STATUS)
            .order_by('section_number')
            .prefetch_related(Prefetch('lesson_set', queryset=lesson_qs))
        )
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
    document = serializers.CharField()
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
        include_drafts = self.context.get('include_drafts', False)
        hws = filter_homework_queryset_for_visibility(
            obj.homework_set.all(), include_drafts
        )
        return {
            'document': obj.document or '',
            'recording_url': 'https://example.com/recordings/mock-lesson',
            'started_at': '2026-01-15T10:00:00+00:00',
            'homeworks': [
                {
                    'homework_id': h.homework_id,
                    'title': h.title,
                    'homework_slug': h.slug,
                    'deadline': h.deadline,
                }
                for h in hws
            ],
        }


class LessonDocumentStrField(serializers.Field):
    """
    Фронт шлёт либо JSON-объект (в теле application/json), либо строку (после multipart).
    Внутри пайплайна — одна JSON-строка с плейсхолдерами local://n.
    """

    def to_internal_value(self, data):
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False)
        raise serializers.ValidationError('document: ожидается JSON-объект или строка JSON.')


class LessonAssetPayloadSerializer(serializers.Serializer):
    asset_id = serializers.IntegerField(min_value=1)
    asset_type = serializers.CharField(max_length=64)
    asset_file = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=True,
        help_text='Имя поля FormData с файлом, по умолчанию asset_<asset_id>',
    )


class LessonContentPayloadSerializer(serializers.Serializer):
    document = LessonDocumentStrField()
    assets = LessonAssetPayloadSerializer(many=True, required=False, default=list)


class LessonCreateSerializer(serializers.Serializer):
    """
    POST /api/courses/{slug}/lessons/: section, title, type, опционально content.
    content: { document (JSON-строка или объект), assets: [{ asset_id, asset_type, asset_file? }] }.
    Файлы в multipart: поля asset_1, asset_2 или имена из asset_file.
    """

    section = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(),
        required=False,
        allow_null=True,
    )
    title = serializers.CharField(max_length=120)
    type = serializers.ChoiceField(
        choices=Lesson._meta.get_field('type').choices,
        default=PublishableMixin.DRAFT_STATUS,
        required=False,
    )
    content = LessonContentPayloadSerializer(required=False, allow_null=True)

    def to_internal_value(self, data):
        if hasattr(data, 'get'):
            raw = data.get('content')
            if isinstance(raw, str):
                stripped = raw.strip()
                if not stripped:
                    if hasattr(data, '_mutable'):
                        data = data.copy()
                    else:
                        data = dict(data) if isinstance(data, dict) else data.copy()
                    data['content'] = None
                else:
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError as e:
                        raise serializers.ValidationError(
                            {'content': 'Невалидный JSON в поле content.'}
                        ) from e
                    if hasattr(data, '_mutable'):
                        data = data.copy()
                    else:
                        data = dict(data) if isinstance(data, dict) else data.copy()
                    data['content'] = parsed
        return super().to_internal_value(data)

    def validate_section(self, section):
        course = self.context.get('course')
        if course is None:
            return section
        if section is not None and section.course_id != course.course_id:
            raise serializers.ValidationError('Секция не принадлежит этому курсу.')
        return section

    def create(self, validated_data):
        content_payload = validated_data.pop('content', None)
        lesson = Lesson.objects.create(**validated_data)
        if content_payload is not None:
            doc_str = content_payload['document']
            assets = list(content_payload.get('assets') or [])
            try:
                resolved = resolve_lesson_document_string(
                    self.context['course'].course_id,
                    lesson.lesson_id,
                    doc_str,
                    assets,
                    self.context['request'].FILES,
                )
            except ValueError as e:
                lesson.delete()
                raise serializers.ValidationError({'content': str(e)}) from e
            lesson.document = resolved
            lesson.save(update_fields=['document'])
        return lesson

    def to_representation(self, instance):
        data = LessonSerializer(instance).data
        doc = data.pop('document', '')
        data['content'] = {'document': doc, 'assets': []}
        return data


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
        extra_kwargs = {
            'lesson': {'required': False},
        }
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


class WebinarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webinar
        fields = [
            'webinar_id', 'lesson', 'status',
            'started_by', 'started_at', 'ended_at',
            'recording_url',
        ]
        read_only_fields = [
            'webinar_id', 'started_by', 'started_at',
            'ended_at', 'recording_url',
        ]


class UserWebinarListItemSerializer(serializers.Serializer):

    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    lesson_title = serializers.CharField()
    lesson_slug = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)


class WebinarTokenSerializer(serializers.Serializer):
    rtc_token = serializers.CharField()
    agora_app_id = serializers.CharField()
    channel_name = serializers.CharField()
    uid = serializers.IntegerField()
    whiteboard_app_id = serializers.CharField()
    whiteboard_room_uuid = serializers.CharField()
    whiteboard_room_token = serializers.CharField()
    whiteboard_region = serializers.CharField()
    role = serializers.CharField()
