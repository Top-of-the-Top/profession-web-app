from ..models import Course, PurchasedCourse, Lesson, Homework, Section, Question, Task
from apps.users.models import User
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()
    authors = serializers.PrimaryKeyRelatedField(many=True, read_only=False, required=False, queryset=User.objects.all())

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('course_id', 'created_at', 'updated_at')


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
        read_only_fields = ('section_id', 'section_number', 'created_at', 'updated_at')


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


class CourseHomePageSerializer(serializers.Serializer):
    course_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    content = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()

    @extend_schema_field(SectionWithLessonsAndTypeSerializer(many=True))
    def get_content(self, obj):
        sections = Section.objects.filter(course=obj).order_by('section_number')
        is_author = self.context.get('is_author', False)

        if is_author:
            return SectionWithLessonsAndTypeSerializer(sections, many=True).data
        else:
            return SectionWithLessonsSerializer(sections, many=True).data

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_meta(self, obj):
        #TODO: сделать метаданные курса
        return {}


class LessonSerializer(serializers.ModelSerializer):
    section = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ('lesson_id', 'lesson_number', 'created_at', 'updated_at')

class HomeworkItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['question', 'task'])
    id = serializers.UUIDField(required=False, allow_null=True)
    number = serializers.IntegerField(read_only=True)
    text = serializers.CharField(max_length=200)
    answer_options = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True
    )
    correct_ans = serializers.CharField(required=False, allow_null=True)
    max_points = serializers.IntegerField(required=False, allow_null=True, default=0)
    created_at = serializers.DateTimeField(read_only=True)


class HomeworkSerializer(serializers.ModelSerializer):
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
        read_only_fields = ('homework_id', 'homework_number', 'created_at', 'updated_at')

    @extend_schema_field(HomeworkItemSerializer(many=True))
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

        items.sort(key=lambda x: x['created_at'])
        return items


class HomeworkCreateSerializer(serializers.Serializer):
    lesson_id = serializers.UUIDField()
    title = serializers.CharField(max_length=120)
    deadline = serializers.DateTimeField()
    items = HomeworkItemSerializer(many=True, required=False, default=list)

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        lesson_id = validated_data.pop('lesson_id')

        homework = Homework.objects.create(
            lesson_id=lesson_id,
            **validated_data
        )

        for item in items_data:
            item_type = item.get('type')
            if item_type == 'question':
                Question.objects.create(
                    homework=homework,
                    text=item['text'],
                    answer_options=item.get('answer_options', []),
                    correct_ans=item.get('correct_ans', ''),
                )
            elif item_type == 'task':
                Task.objects.create(
                    homework=homework,
                    text=item['text'],
                    max_points=item.get('max_points', 0),
                )

        return homework

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        instance.title = validated_data.get('title', instance.title)
        instance.deadline = validated_data.get('deadline', instance.deadline)
        instance.save()

        if items_data is not None:
            existing_question_ids = set(
                instance.question_set.values_list('question_id', flat=True)
            )
            existing_task_ids = set(
                instance.task_set.values_list('task_id', flat=True)
            )

            received_question_ids = set()
            received_task_ids = set()

            for item in items_data:
                item_type = item.get('type')
                item_id = item.get('id')

                if item_type == 'question':
                    if item_id and item_id in existing_question_ids:
                        Question.objects.filter(question_id=item_id).update(
                            text=item['text'],
                            answer_options=item.get('answer_options', []),
                            correct_ans=item.get('correct_ans', ''),
                        )
                        received_question_ids.add(item_id)
                    else:
                        new_question = Question.objects.create(
                            homework=instance,
                            text=item['text'],
                            answer_options=item.get('answer_options', []),
                            correct_ans=item.get('correct_ans', ''),
                        )
                        received_question_ids.add(new_question.question_id)

                elif item_type == 'task':
                    if item_id and item_id in existing_task_ids:
                        Task.objects.filter(task_id=item_id).update(
                            text=item['text'],
                            max_points=item.get('max_points', 0),
                        )
                        received_task_ids.add(item_id)
                    else:
                        new_task = Task.objects.create(
                            homework=instance,
                            text=item['text'],
                            max_points=item.get('max_points', 0),
                        )
                        received_task_ids.add(new_task.task_id)

            questions_to_delete = existing_question_ids - received_question_ids
            tasks_to_delete = existing_task_ids - received_task_ids

            if questions_to_delete:
                Question.objects.filter(question_id__in=questions_to_delete).delete()
            if tasks_to_delete:
                Task.objects.filter(task_id__in=tasks_to_delete).delete()

        return instance


class TaskSerializer(serializers.ModelSerializer):
    homework = serializers.PrimaryKeyRelatedField(
        queryset=Homework.objects.all(), required=False
    )

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ('task_id', 'task_number', 'created_at', 'updated_at')


class QuestionSerializer(serializers.ModelSerializer):
    homework = serializers.PrimaryKeyRelatedField(
        queryset=Homework.objects.all(), required=False
    )

    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ('question_id', 'question_number', 'created_at', 'updated_at')
