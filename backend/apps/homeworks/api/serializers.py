from rest_framework import serializers
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema_field

from apps.core.meta_management.factory import build_access_api

from ..models import Attempt


NOT_REVIEWED_LABEL = 'не проверено'
TASK_ATTACHMENT_CONTEXT_KEY = 'task_attachments_by_answer_id'


class FileAttachmentSerializer(serializers.Serializer):
    attachment_id = serializers.UUIDField()
    file_name = serializers.CharField(max_length=255)
    file_url = serializers.URLField(allow_null=True)
    file_size = serializers.IntegerField(min_value=0)
    file_extension = serializers.CharField(max_length=16)


def _derive_extension(filename, mime_type):
    if filename and '.' in filename:
        return filename.rsplit('.', 1)[-1].lower()[:16]
    if mime_type and '/' in mime_type:
        return mime_type.split('/')[-1].lower()[:16]
    return ''


def build_task_attachments_map(task_answers, viewer=None, access=None):
    access = access or build_access_api()
    try:
        raw_map = access.resolve_bound_assets_map(
            task_answers, role='task_attachment', viewer=viewer,
        )
    except Exception:
        raw_map = {}

    result = {}
    for answer_id, items in raw_map.items():
        serialized = []
        for item in items:
            asset = item['asset']
            serialized.append({
                'attachment_id': str(asset.asset_id),
                'file_name': asset.original_filename or '',
                'file_url': item['url'],
                'file_size': asset.size_bytes or 0,
                'file_extension': _derive_extension(
                    asset.original_filename, asset.mime_type,
                ),
            })
        result[str(answer_id)] = serialized
    return result


class QuestionAttemptItemSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    question_id = serializers.UUIDField(source='question.question_id', read_only=True)
    answer_id = serializers.UUIDField(read_only=True)
    status = serializers.SerializerMethodField()
    number = serializers.IntegerField(source='question.question_number', read_only=True)
    text = serializers.CharField(source='question.text', read_only=True)
    answer_options = serializers.JSONField(source='question.answer_options', read_only=True)
    user_answer = serializers.CharField(read_only=True, allow_null=True)
    max_points = serializers.IntegerField(source='question.max_points', read_only=True)

    def get_type(self, obj):
        return 'question'

    def get_status(self, obj):
        return obj.status or NOT_REVIEWED_LABEL


class ReviewerSerializer(serializers.Serializer):
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_avatar_url(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile is None:
            return None
        return profile.avatar_url or None


class TaskReviewReadSerializer(serializers.Serializer):
    task_review_id = serializers.UUIDField(read_only=True)
    points = serializers.IntegerField(read_only=True)
    comment = serializers.CharField(read_only=True, allow_null=True)
    reviewer = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    @extend_schema_field(ReviewerSerializer(allow_null=True))
    def get_reviewer(self, obj):
        if obj.reviewer is None:
            return None
        return ReviewerSerializer(obj.reviewer).data


class TaskAttemptItemSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    task_id = serializers.UUIDField(source='task.task_id', read_only=True)
    answer_id = serializers.UUIDField(read_only=True)
    status = serializers.SerializerMethodField()
    number = serializers.IntegerField(source='task.task_number', read_only=True)
    text = serializers.CharField(source='task.text', read_only=True)
    user_answer = serializers.CharField(read_only=True, allow_null=True)
    max_points = serializers.IntegerField(source='task.max_points', read_only=True)
    review = serializers.SerializerMethodField()
    file_attachments = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'task'

    def get_status(self, obj):
        return obj.status or NOT_REVIEWED_LABEL

    @extend_schema_field(TaskReviewReadSerializer(allow_null=True))
    def get_review(self, obj):
        try:
            review = obj.review
        except AttributeError:
            return None
        return TaskReviewReadSerializer(review).data

    @extend_schema_field(FileAttachmentSerializer(many=True))
    def get_file_attachments(self, obj):
        mapping = self.context.get(TASK_ATTACHMENT_CONTEXT_KEY)
        if mapping is not None:
            return mapping.get(str(obj.answer_id), [])

        request = self.context.get('request')
        viewer = getattr(request, 'user', None) if request is not None else None
        fallback = build_task_attachments_map([obj], viewer=viewer)
        return fallback.get(str(obj.answer_id), [])


class AttemptSerializer(serializers.ModelSerializer):

    homework_id = serializers.UUIDField(source='homework.homework_id', read_only=True)
    deadline = serializers.DateTimeField(source='homework.deadline', read_only=True)
    score = serializers.IntegerField(source='grade', read_only=True, allow_null=True)
    max_points = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = (
            'homework_id',
            'attempt_id',
            'status',
            'deadline',
            'score',
            'max_points',
            'items',
        )
        read_only_fields = fields

    def get_max_points(self, obj):
        homework = obj.homework
        questions_total = sum(
            q.max_points for q in homework.question_set.all()
        )
        tasks_total = sum(
            t.max_points for t in homework.task_set.all()
        )
        return questions_total + tasks_total

    @extend_schema_field(PolymorphicProxySerializer(
        component_name='AttemptItem',
        resource_type_field_name='type',
        serializers={
            'question': QuestionAttemptItemSerializer,
            'task': TaskAttemptItemSerializer,
        },
        many=True,
    ))
    def get_items(self, obj):
        task_answers = list(obj.task_answers.select_related('task', 'review', 'review__reviewer', 'review__reviewer__profile').all())

        request = self.context.get('request')
        viewer = getattr(request, 'user', None) if request is not None else None
        ctx = dict(self.context)
        ctx[TASK_ATTACHMENT_CONTEXT_KEY] = build_task_attachments_map(
            task_answers, viewer=viewer,
        )

        question_items = QuestionAttemptItemSerializer(
            obj.question_answers.select_related('question').all(),
            many=True,
            context=ctx,
        ).data
        task_items = TaskAttemptItemSerializer(
            task_answers,
            many=True,
            context=ctx,
        ).data

        items = list(question_items) + list(task_items)
        items.sort(key=lambda item: item.get('number') or 0)
        return items


class AttemptListSerializer(serializers.ModelSerializer):
  homework_id = serializers.UUIDField(source='homework.homework_id', read_only=True)
  homework_slug = serializers.SlugField(source='homework.slug', read_only=True)
  deadline = serializers.DateTimeField(source='homework.deadline', read_only=True)
  score = serializers.IntegerField(source='grade', read_only=True, allow_null=True)
  max_points = serializers.SerializerMethodField()

  class Meta:
    model = Attempt
    fields = (
      'attempt_id',
      'homework_id',
      'deadline',
      'homework_slug',
      'status',
      'send_at',
      'score',
      'max_points',
    )

  def get_max_points(self, obj):
    homework = obj.homework
    questions_total = sum(
      q.max_points for q in homework.question_set.all()
    )
    tasks_total = sum(
      t.max_points for t in homework.task_set.all()
    )
    return questions_total + tasks_total

class SubmitQuestionItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['question'])
    id = serializers.UUIDField()
    number = serializers.IntegerField(min_value=1)
    user_answer = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class SubmitTaskItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['task'])
    id = serializers.UUIDField()
    number = serializers.IntegerField(min_value=1)
    user_answer = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    asset_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


@extend_schema_field(PolymorphicProxySerializer(
    component_name='SubmitItem',
    resource_type_field_name='type',
    serializers={
        'question': SubmitQuestionItemSerializer,
        'task': SubmitTaskItemSerializer,
    },
))
class SubmitItemField(serializers.Field):

    _ITEM_SERIALIZERS = {
        'question': SubmitQuestionItemSerializer,
        'task': SubmitTaskItemSerializer,
    }

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError('Элемент должен быть объектом.')

        item_type = data.get('type')
        child_cls = self._ITEM_SERIALIZERS.get(item_type)
        if child_cls is None:
            raise serializers.ValidationError(
                {'type': 'Поле type обязательно и должно быть "question" или "task".'}
            )

        child = child_cls(data=data, context=self.context)
        child.is_valid(raise_exception=True)
        return dict(child.validated_data)

    def to_representation(self, value):
        return value


class AttemptSubmitSerializer(serializers.Serializer):
    homework_id = serializers.UUIDField()
    attempt_id = serializers.UUIDField()
    send_at = serializers.DateTimeField()
    items = serializers.ListField(child=SubmitItemField(), allow_empty=False)


class TaskReviewItemSerializer(serializers.Serializer):
    task_answer_id = serializers.UUIDField()
    points = serializers.IntegerField(min_value=0)
    comment = serializers.CharField(
        max_length=1500, allow_blank=True, allow_null=True, required=False, default=None
    )

class AttemptReviewSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    items = serializers.ListField(child=TaskReviewItemSerializer(), allow_empty=False)


class ErrorDetailItemSerializer(serializers.Serializer):
    number = serializers.IntegerField()
    issue = serializers.CharField()


class ErrorDetailsSerializer(serializers.Serializer):
    items = ErrorDetailItemSerializer(many=True, required=False)


class ErrorResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='error')
    code = serializers.CharField()
    message = serializers.CharField()
    details = ErrorDetailsSerializer(required=False)
