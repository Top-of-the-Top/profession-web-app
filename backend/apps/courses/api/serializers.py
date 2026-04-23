from .permissions import filter_homework_queryset_for_visibility
import json

from ..models import (
    Course,
    PurchasedCourse,
    Lesson,
    Homework,
    Section,
    Question,
    Task,
    PublishableMixin,
)
from ..lesson_content import extract_asset_ids, parse_content_value, substitute_asset_uris
from django.db.models import Prefetch
from apps.users.models import User
from apps.core.services.factory import build_access_api
from apps.core.services.errors import AssetError
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


COURSE_COVER_CONTEXT_KEY = 'cover_url_by_course_id'


def _resolve_course_cover_url(course, context=None, access=None):
    context = context or {}
    cover_map = context.get(COURSE_COVER_CONTEXT_KEY)
    if cover_map is not None:
        url = cover_map.get(str(course.course_id))
        return url or course.image_url

    access = access or build_access_api()
    try:
        url = access.resolve_bound_url(course, role='course_cover')
    except Exception:
        url = None
    return url or course.image_url


def build_course_cover_map(courses, access=None):
    access = access or build_access_api()
    try:
        return access.resolve_bound_urls_map(courses, role='course_cover')
    except Exception:
        return {}


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    authors = serializers.PrimaryKeyRelatedField(
        many=True, read_only=False, required=False, queryset=User.objects.all()
    )

    class Meta:
        model = Course
        exclude = ('image',)
        read_only_fields = ('course_id', 'created_at', 'updated_at', 'last_modified_by')

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_url(self, obj):
        return _resolve_course_cover_url(obj, self.context)


class CourseDTOSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

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

    @extend_schema_field(OpenApiTypes.URI)
    def get_image_url(self, obj):
        return _resolve_course_cover_url(obj, self.context)


class CourseCoverBindRequestSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField(required=True)


class CourseCoverResponseSerializer(serializers.Serializer):
    cover = serializers.URLField(allow_null=True)


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
    type = serializers.CharField()


class LessonContentReadSerializer(serializers.Serializer):
    document = serializers.CharField()
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    webinar_status = serializers.CharField(allow_null=True)
    recordings = serializers.ListField(child=serializers.DictField())
    homeworks = HomeworkBriefSerializer(many=True)


class LessonDetailReadSerializer(serializers.ModelSerializer):
    lesson_id = serializers.UUIDField(read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ('lesson_id', 'title', 'content')

    @extend_schema_field(LessonContentReadSerializer)
    def get_content(self, obj):
        from apps.webinars.api.serializers import (
            RECORDING_WHITEBOARD_CONTEXT_KEY,
            RecordingListItemSerializer,
            build_recording_whiteboard_map,
        )

        include_drafts = self.context.get('include_drafts', False)
        hws = filter_homework_queryset_for_visibility(
            obj.homework_set.all(), include_drafts
        )

        webinar = getattr(obj, 'webinar', None)
        started_at = webinar.started_at if webinar else None
        webinar_status = webinar.status if webinar else None

        if webinar:
            recordings_list = list(
                webinar.recordings.filter(is_deleted=False).order_by('-started_at')
            )
            rec_context = dict(self.context)
            rec_context[RECORDING_WHITEBOARD_CONTEXT_KEY] = build_recording_whiteboard_map(
                recordings_list,
            )
            recordings_data = RecordingListItemSerializer(
                recordings_list, many=True, context=rec_context,
            ).data
        else:
            recordings_data = []

        document = obj.document or ''
        asset_ids = extract_asset_ids(document)
        if asset_ids:
            request = self.context.get('request')
            viewer = getattr(request, 'user', None) if request is not None else None
            access = build_access_api()
            try:
                uri_to_url = access.resolve_many_for_viewer(asset_ids, viewer=viewer)
            except Exception:
                uri_to_url = {}
            document = substitute_asset_uris(document, uri_to_url)

        return {
            'document': document,
            'started_at': started_at,
            'webinar_status': webinar_status,
            'recordings': recordings_data,
            'homeworks': [
                {
                    'homework_id': h.homework_id,
                    'title': h.title,
                    'homework_slug': h.slug,
                    'deadline': h.deadline,
                    'type': h.type,
                }
                for h in hws
            ],
        }


class LessonSimpleCreateSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Lesson
        fields = ('section', 'title', 'type')

    def validate(self, attrs):
        request = self.context.get('request')
        if request is not None:
            data = getattr(request, 'data', None)
            if data is not None and data.get('content') is not None:
                raise serializers.ValidationError(
                    {
                        'content': 'Создание с контентом и вложениями выполняйте запросом '
                        'PUT на этот же URL.'
                    }
                )
        return attrs

    def validate_section(self, section):
        course = self.context.get('course')
        if course is None:
            return section
        if section is not None and section.course_id != course.course_id:
            raise serializers.ValidationError('Секция не принадлежит этому курсу.')
        return section


class LessonDocumentStrField(serializers.Field):
    def to_internal_value(self, data):
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False)
        raise serializers.ValidationError('document: ожидается JSON-объект или строка JSON.')


class LessonContentPayloadSerializer(serializers.Serializer):
    document = LessonDocumentStrField()


class LessonCreateSerializer(serializers.Serializer):
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
        if not hasattr(data, 'get'):
            return super().to_internal_value(data)

        raw_content = data.get('content')
        normalized_content = raw_content

        if isinstance(raw_content, str):
            stripped = raw_content.strip()
            if not stripped:
                normalized_content = None
            else:
                try:
                    normalized_content = json.loads(raw_content)
                except json.JSONDecodeError as e:
                    raise serializers.ValidationError(
                        {'content': 'Невалидный JSON в поле content.'}
                    ) from e

        payload = {
            'content': normalized_content,
        }
        title_sentinel = object()
        raw_title = data.get('title', title_sentinel)
        if raw_title is not title_sentinel:
            payload['title'] = raw_title
        raw_section = data.get('section')
        if raw_section not in (None, ''):
            payload['section'] = raw_section
        raw_type = data.get('type')
        if raw_type not in (None, ''):
            payload['type'] = raw_type

        return super().to_internal_value(payload)

    def validate_section(self, section):
        course = self.context.get('course')
        if course is None:
            return section
        if section is not None and section.course_id != course.course_id:
            raise serializers.ValidationError('Секция не принадлежит этому курсу.')
        return section

    def _sync_lesson_assets(self, lesson, document_str):
        from apps.core.services.factory import build_binding_api

        asset_ids = extract_asset_ids(document_str)
        binding = build_binding_api()
        binding.sync_many(
            content_object=lesson,
            role='lesson_block',
            asset_ids=asset_ids,
            owner=None,
        )

    def _extract_content_payload(self, validated_data):
        content_payload = validated_data.pop('content', None)
        if content_payload is not None:
            return content_payload

        initial_data = getattr(self, 'initial_data', None)
        if hasattr(initial_data, 'get'):
            raw = initial_data.get('content')
        elif isinstance(initial_data, dict):
            raw = initial_data.get('content')
        else:
            raw = None

        parsed = parse_content_value(raw)
        if parsed is None:
            return None

        serializer = LessonContentPayloadSerializer(data=parsed)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def create(self, validated_data):
        content_payload = self._extract_content_payload(validated_data)
        lesson = Lesson.objects.create(**validated_data)
        if content_payload is not None:
            document_str = content_payload['document']
            lesson.document = document_str
            lesson.save(update_fields=['document'])
            try:
                self._sync_lesson_assets(lesson, document_str)
            except AssetError as e:
                lesson.delete()
                raise serializers.ValidationError({'content': e.message}) from e
        return lesson

    def update(self, instance, validated_data):
        content_payload = self._extract_content_payload(validated_data)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        update_fields = list(validated_data.keys())

        if content_payload is not None:
            instance.document = content_payload['document']
            update_fields.append('document')

        if update_fields:
            instance.save(update_fields=update_fields)

        if content_payload is not None:
            try:
                self._sync_lesson_assets(instance, content_payload['document'])
            except AssetError as e:
                raise serializers.ValidationError({'content': e.message}) from e

        return instance

    def to_representation(self, instance):
        data = LessonSerializer(instance).data
        doc = data.pop('document', '')
        data['content'] = {'document': doc}
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
                'max_points': q.max_points,
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


class UserWebinarListItemSerializer(serializers.Serializer):
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    lesson_title = serializers.CharField()
    lesson_slug = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
