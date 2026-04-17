from django.db import models
import os
from django.core.exceptions import ValidationError
from ..users.models import User
import uuid
from slugify import slugify

DEFAULT_COURSE_IMAGE = "courses/default_course.png"

class TimestampedMixin(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class PublishableMixin(models.Model):
    DRAFT_STATUS = 'draft'
    PUBLISHED_STATUS = 'published'

    STATUS_CHOICES = [
        (DRAFT_STATUS, 'черновик'),
        (PUBLISHED_STATUS, 'опубликован'),
    ]

    type = models.CharField(
        max_length=20,
        default=DRAFT_STATUS,
        choices=STATUS_CHOICES,
        verbose_name='Статус'
    )

    class Meta:
        abstract = True

class AbstractComponentModel(PublishableMixin, TimestampedMixin):
    """Абстрактная модель для отслеживания автора изменений"""

    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто изменил",
        related_name="%(class)s_modifications"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']

class AutoIncrementMixin(models.Model):

    def _generate_next_number(self, parent_field, number_field):
        if not getattr(self, number_field):
            parent_value = getattr(self, parent_field)
            filter_kwargs = {parent_field: parent_value}

            last_item = self.__class__.objects.filter(**filter_kwargs).order_by(number_field).last()

            if last_item:
                setattr(self, number_field, getattr(last_item, number_field) + 1)
            else:
                setattr(self, number_field, 1)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

def course_image_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    photo_uuid = uuid.uuid4()
    return f'courses/course_{photo_uuid}.{ext}'

def generate_unique_slug(instance, title, slug_field='slug'):
    base_slug = slugify(title[:80])
    if not base_slug:
        base_slug = 'title'

    uuid_part = str(uuid.uuid4()).split('-')[0][:8]
    return f"{base_slug}-{uuid_part}"


class Course(AbstractComponentModel):
    course_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    authors = models.ManyToManyField(
        User,
        related_name='authored_courses',
        verbose_name='Авторы курса'
    )
    title = models.CharField(max_length=50, verbose_name='Название курса')
    sub_title = models.CharField(max_length=75, verbose_name='Краткое описание курса')
    description = models.TextField(verbose_name="Описание курса")
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    price = models.PositiveIntegerField(verbose_name='Цена')
    image = models.ImageField(
        upload_to=course_image_path,
        blank=True,
        null=True,
        verbose_name='Изображение курса',
        default=DEFAULT_COURSE_IMAGE,
    )
    kinescope_folder_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='Kinescope folder id'
    )

    @property
    def image_url(self):
        if self.image and self.image.name != DEFAULT_COURSE_IMAGE:
            return self.image.url
        bucket = os.getenv("AWS_S3_BUCKET_NAME", "your-bucket")
        return f'https://storage.yandexcloud.net/{bucket}/{DEFAULT_COURSE_IMAGE}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)

        if is_new and self.image and hasattr(self.image, 'file') and self.image.name != DEFAULT_COURSE_IMAGE:
            image_file = self.image.file
            original_name = getattr(self.image, 'name', 'image.jpg')

            self.image = None
            super().save(*args, **kwargs)

            ext = original_name.split('.')[-1].lower() if '.' in original_name else 'jpg'
            new_name = f'courses/course_{self.pk}.{ext}'

            image_file.seek(0)
            self.image.save(new_name, image_file, save=False)
            super().save(update_fields=['image'])
        else:
            super().save(*args, **kwargs)


    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Section(AbstractComponentModel, AutoIncrementMixin):
    section_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    section_number = models.PositiveIntegerField(verbose_name='Номер секции', blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='ID курса')
    title = models.CharField(max_length=120, verbose_name='Название секции')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)

        self._generate_next_number(parent_field='course', number_field='section_number')

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Секция'
        verbose_name_plural = 'Секции'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['section_number']),
        ]

class Lesson(AbstractComponentModel, AutoIncrementMixin):
    lesson_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    lesson_number = models.PositiveIntegerField(verbose_name='Номер урока', blank=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, verbose_name='ID секции')
    title = models.CharField(max_length=120, verbose_name='Название урока')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    document = models.TextField(
        blank=True,
        default='',
        verbose_name='JSON урока после подстановки URL (local:// → хранилище)',
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        self._generate_next_number(parent_field='section', number_field='lesson_number')

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lesson_number']),
        ]


class Homework(AbstractComponentModel, AutoIncrementMixin):
    homework_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    homework_number = models.PositiveIntegerField(verbose_name='Номер домашнего задания', blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name='Название домашнего задания')
    slug = models.SlugField(max_length=120, verbose_name='URL', blank=True)
    deadline = models.DateTimeField(verbose_name='Дедлайн')


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)
        self._generate_next_number(parent_field='lesson', number_field='homework_number')

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Домашнее задание'
        verbose_name_plural = 'Домашние задания'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['homework_number']),
        ]

    def __str__(self):
        return self.title


class Question(AbstractComponentModel, AutoIncrementMixin):
    question_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    question_number = models.PositiveIntegerField(verbose_name='Номер вопроса', blank=True)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, verbose_name='Текст вопроса')
    correct_ans = models.CharField(verbose_name='Правильный ответ на вопрос')
    answer_options = models.JSONField(verbose_name='Варианты ответов')


    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['question_number']),
        ]

    def save(self, *args, **kwargs):
        self._generate_next_number(parent_field='homework', number_field='question_number')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class Task(AbstractComponentModel, AutoIncrementMixin):
    task_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    task_number = models.PositiveIntegerField(verbose_name='Номер задания', blank=True)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, verbose_name='Текст задания')
    max_points = models.PositiveIntegerField(default=0, verbose_name='Максимальное количество баллов за задание')


    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['task_number']),
        ]
    def save(self, *args, **kwargs):
        self._generate_next_number(parent_field='homework', number_field='task_number')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text

class PurchasedCourse(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='purchased_courses',
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='purchases',
    )

    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.CASCADE,
        related_name='purchased_courses',
    )
    access_expires_at = models.DateTimeField()

    class Meta:
        db_table = 'courses_by_user'
        verbose_name = 'Купленный курс'
        verbose_name_plural = 'Купленные курсы'
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user} → {self.course}'

    @property
    def is_active(self):
        from django.utils import timezone
        return timezone.now() < self.access_expires_at
    

class Webinar(TimestampedMixin):
    PENDING_STATUS = 'pending'
    LIVE_STATUS = 'live'
    ENDED_STATUS = 'ended'

    STATUS_CHOICES = [
        (PENDING_STATUS, 'Ожидание'),
        (LIVE_STATUS, 'В эфире'),
        (ENDED_STATUS, 'Завершен'),
    ]

    webinar_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name='id',
    )
    lesson = models.OneToOneField(
        Lesson, 
        on_delete=models.CASCADE,
        related_name='webinar',
        verbose_name='Урок'
    )
    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='started_webinars',
        verbose_name='Кто запустил',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING_STATUS,
        verbose_name='Статус',
    )

    agora_channel_name = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        verbose_name='Agora Channel Name',
    )

    whiteboard_room_uuid = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='Whiteboard Room UUID',
    )

    recording_resource_id = models.CharField(
        max_length=256,
        blank=True,
    )
    recording_sid = models.CharField(
        max_length=256,
        blank=True,
    )
    recording_url = models.URLField(
        blank=True,
        verbose_name='Ссылка на запись',
    )

    KINESCOPE_UPLOAD_STATUS_CHOICES = [
        ('none', 'Нет загрузки'),
        ('pending', 'В очереди'),
        ('uploading', 'Загружается'),
        ('processing', 'Обрабатывается'),
        ('ready', 'Готово'),
        ('failed', 'Ошибка'),
    ]
    kinescope_video_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='Kenescope video id',
    )
    kinescope_upload_status = models.CharField(
        max_length=20,
        null=False,
        choices=KINESCOPE_UPLOAD_STATUS_CHOICES,
        default='none',
        verbose_name='Статут загрузки в кинескоп',
    )    


    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Начало',
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Конец',
    )

    def save(self, *args, **kwargs):
        if not self.agora_channel_name:
            self.agora_channel_name = f"webinar-{str(self.lesson.lesson_id)[:8]}"
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Вебинар'
        verbose_name_plural = 'Вебинары'
        ordering = ['-created_at']

    def __str__(self):
        return f"Вебинар: {self.lesson.title}"
    