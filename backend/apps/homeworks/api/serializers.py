from rest_framework import serializers
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema_field

from ..models import Attempt, QuestionAnswer, TaskAnswer


NOT_REVIEWED_LABEL = 'не проверено'
QUESTION_MAX_POINTS = 1

class FileAttachmentSerializer(serializers.Serializer):
    attachment_id = serializers.UUIDField()
    file_name = serializers.CharField(max_length=255)
    file_url = serializers.URLField()
    file_size = serializers.IntegerField(min_value=0)
    file_format = serializers.CharField(max_length=16)


class QuestionAttemptItemSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    question_id = serializers.UUIDField(source='question.question_id', read_only=True)
    answer_id = serializers.UUIDField(read_only=True)
    status = serializers.SerializerMethodField()
    number = serializers.IntegerField(source='question.question_number', read_only=True)
    text = serializers.CharField(source='question.text', read_only=True)
    answer_options = serializers.JSONField(source='question.answer_options', read_only=True)
    user_answer = serializers.CharField(read_only=True, allow_null=True)
    max_points = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'question'

    def get_status(self, obj):
        return obj.status or NOT_REVIEWED_LABEL

    def get_max_points(self, obj):
        return QUESTION_MAX_POINTS


class TaskAttemptItemSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    task_id = serializers.UUIDField(source='task.task_id', read_only=True)
    answer_id = serializers.UUIDField(read_only=True)
    status = serializers.SerializerMethodField()
    number = serializers.IntegerField(source='task.task_number', read_only=True)
    text = serializers.CharField(source='task.text', read_only=True)
    user_answer = serializers.CharField(read_only=True, allow_null=True)
    points = serializers.SerializerMethodField()
    max_points = serializers.IntegerField(source='task.max_points', read_only=True)
    teacher_comment = serializers.SerializerMethodField()
    file_attachments = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'task'

    def get_status(self, obj):
        return obj.status or NOT_REVIEWED_LABEL

    def get_points(self, obj):
        return getattr(obj, 'points', None)

    def get_teacher_comment(self, obj):
        return getattr(obj, 'teacher_comment', None)

    @extend_schema_field(FileAttachmentSerializer(many=True))
    def get_file_attachments(self, obj):
        return []


class AttemptSerializer(serializers.ModelSerializer):

    homework_id = serializers.UUIDField(source='homework.homework_id', read_only=True)
    deadline = serializers.DateTimeField(source='homework.deadline', read_only=True)
    score = serializers.IntegerField(source='grade', read_only=True, allow_null=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = (
            'homework_id',
            'attempt_id',
            'status',
            'deadline',
            'score',
            'items',
        )
        read_only_fields = fields

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
        question_items = QuestionAttemptItemSerializer(
            obj.question_answers.select_related('question').all(),
            many=True,
            context=self.context,
        ).data
        task_items = TaskAttemptItemSerializer(
            obj.task_answers.select_related('task').all(),
            many=True,
            context=self.context,
        ).data

        items = list(question_items) + list(task_items)
        items.sort(key=lambda item: item.get('number') or 0)
        return items


class AttemptListSerializer(serializers.ModelSerializer):
  homework_id = serializers.UUIDField(source='homework.homework_id', read_only=True)
  homework_slug = serializers.UUIDField(source='homework.slug', read_only=True)
  deadline = serializers.DateTimeField(source='homework.deadline', read_only=True)
  score = serializers.IntegerField(source='grade', read_only=True, allow_null=True)
  class Meta:
    model = Attempt
    fields = ('attempt_id', 'homework_id', 'deadline', 'homework_slug', 'status', 'send_at', 'score')

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
    file_attachments = FileAttachmentSerializer(many=True, required=False, default=list)


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


class UploadFileRequestSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    task_id = serializers.UUIDField()
    file_name = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField(min_value=1)
    file_format = serializers.CharField(max_length=16)


class S3UploadFieldsSerializer(serializers.Serializer):
    key = serializers.CharField(help_text="Путь к файлу в S3")
    policy = serializers.CharField(help_text="Base64 policy condition")
    x_amz_algorithm = serializers.CharField(source='x-amz-algorithm')
    x_amz_credential = serializers.CharField(source='x-amz-credential')
    x_amz_date = serializers.CharField(source='x-amz-date')
    x_amz_signature = serializers.CharField(source='x-amz-signature')

class S3UploadResponseSerializer(serializers.Serializer):
    url = serializers.URLField(help_text="URL бакета (endpoint)")
    method = serializers.CharField(default="POST", help_text="HTTP метод для загрузки")
    expires_at = serializers.DateTimeField(help_text="Ссылка истекает в")
    fields = S3UploadFieldsSerializer()


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
