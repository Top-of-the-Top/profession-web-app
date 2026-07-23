import os
import uuid

from django.db import models
from slugify import slugify

from ..users.models import User
from .lesson_content import extract_plain_text

DEFAULT_COURSE_IMAGE = "courses/default_course.png"


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublishableMixin(models.Model):
    DRAFT_STATUS = "draft"
    PUBLISHED_STATUS = "published"

    STATUS_CHOICES = [
        (DRAFT_STATUS, "черновик"),
        (PUBLISHED_STATUS, "опубликован"),
    ]

    type = models.CharField(
        max_length=20,
        default=DRAFT_STATUS,
        choices=STATUS_CHOICES,
        verbose_name="Статус",
    )

    class Meta:
        abstract = True


class AbstractComponentModel(PublishableMixin, TimestampedMixin):

    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто изменил",
        related_name="%(class)s_modifications",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


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
    ext = filename.split(".")[-1].lower()
    photo_uuid = uuid.uuid4()
    return f"courses/course_{photo_uuid}.{ext}"


def generate_unique_slug(title):
    base_slug = slugify(title[:80])
    if not base_slug:
        base_slug = "title"

    uuid_part = str(uuid.uuid4()).split("-")[0][:8]
    return f"{base_slug}-{uuid_part}"


class Course(AbstractComponentModel):
    course_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    authors = models.ManyToManyField(
        User, related_name="authored_courses", verbose_name="Авторы курса"
    )
    title = models.CharField(max_length=50, verbose_name="Название курса")
    sub_title = models.CharField(max_length=75, verbose_name="Краткое описание курса")
    description = models.TextField(verbose_name="Описание курса")
    slug = models.SlugField(max_length=120, verbose_name="URL", blank=True)
    price = models.PositiveIntegerField(verbose_name="Цена")
    image = models.ImageField(
        upload_to=course_image_path,
        blank=True,
        null=True,
        verbose_name="Изображение курса",
        default=DEFAULT_COURSE_IMAGE,
    )
    kinescope_folder_id = models.CharField(
        max_length=64, blank=True, verbose_name="Kinescope folder id"
    )
    yandex_vs_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Yandex Vector Store ID",
    )
    is_deleted = models.BooleanField(default=False, verbose_name="Удалён")
    is_special = models.BooleanField(default=False, verbose_name="Специальный курс")
    starts_at = models.DateField(null=True, blank=True, verbose_name="Дата старта курса")
    duration_weeks = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Длительность курса (недели)"
    )
    min_age = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Минимальный возраст"
    )

    @property
    def image_url(self):
        if self.image and self.image.name != DEFAULT_COURSE_IMAGE:
            return self.image.url
        bucket = os.getenv("AWS_S3_BUCKET_NAME", "your-bucket")
        return f"https://storage.yandexcloud.net/{bucket}/{DEFAULT_COURSE_IMAGE}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not self.slug:
            self.slug = generate_unique_slug(self.title)

        if (
            is_new
            and self.image
            and hasattr(self.image, "file")
            and self.image.name != DEFAULT_COURSE_IMAGE
        ):
            image_file = self.image.file
            original_name = getattr(self.image, "name", "image.jpg")

            self.image = None
            super().save(*args, **kwargs)

            ext = original_name.split(".")[-1].lower() if "." in original_name else "jpg"
            new_name = f"courses/course_{self.pk}.{ext}"

            image_file.seek(0)
            self.image.save(new_name, image_file, save=False)
            super().save(update_fields=["image"])
        else:
            super().save(*args, **kwargs)

    def prepare_full_content_file(self):
        sections = self.section_set.prefetch_related(
            "lesson_set__homework_set__question_set",
            "lesson_set__homework_set__task_set",
        ).order_by("section_number", "created_at")

        chunks = [
            f"Курс: {self.title}",
            f"Краткое описание: {self.sub_title}",
            f"Описание: {self.description}",
        ]

        for section in sections:
            chunks.append(f"\nСекция {section.section_number}: {section.title}")
            lessons = section.lesson_set.order_by("lesson_number", "created_at")
            for lesson in lessons:
                chunks.append(f"  Урок {lesson.lesson_number}: {lesson.title}")
                if lesson.document:
                    plain = extract_plain_text(lesson.document)
                    if plain:
                        chunks.append(f"  Контент урока:\n{plain}")
                homeworks = lesson.homework_set.order_by("homework_number", "created_at")
                for homework in homeworks:
                    chunks.append(
                        f"    Домашнее задание {homework.homework_number}: {homework.title}"
                    )
                    for question in homework.question_set.order_by("question_number", "created_at"):
                        chunks.append(f"      Вопрос {question.question_number}: {question.text}")
                    for task in homework.task_set.order_by("task_number", "created_at"):
                        chunks.append(f"      Задание {task.task_number}: {task.text}")

        return "\n".join(chunks)

    def prepare_files_for_vs(self) -> list[tuple[str, str]]:
        """Возвращает список (filename, content) для загрузки в Vector Store."""
        sections = self.section_set.prefetch_related(
            "lesson_set__homework_set__question_set",
            "lesson_set__homework_set__task_set",
        ).order_by("section_number", "created_at")

        sections_list = list(sections)

        # Overview file
        overview_chunks = [
            f"Курс: {self.title}",
            f"Краткое описание: {self.sub_title}",
            f"Описание: {self.description}",
            "",
            "Структура курса:",
        ]
        for section in sections_list:
            overview_chunks.append(f"  Секция {section.section_number}: {section.title}")
            lessons = section.lesson_set.order_by("lesson_number", "created_at")
            for lesson in lessons:
                overview_chunks.append(f"    Урок {lesson.lesson_number}: {lesson.title}")

        files = [(f"course-{self.pk}-overview.txt", "\n".join(overview_chunks))]

        if not sections_list:
            return files

        # Per-lesson files
        for section in sections_list:
            lessons = section.lesson_set.order_by("lesson_number", "created_at")
            for lesson in lessons:
                lesson_chunks = [
                    f"Курс: {self.title}",
                    f"Секция {section.section_number}: {section.title}",
                    f"Урок {lesson.lesson_number}: {lesson.title}",
                    "",
                ]
                if lesson.document:
                    plain = extract_plain_text(lesson.document)
                    if plain:
                        lesson_chunks.append(plain)
                        lesson_chunks.append("")

                homeworks = lesson.homework_set.order_by("homework_number", "created_at")
                for homework in homeworks:
                    lesson_chunks.append(
                        f"Домашнее задание {homework.homework_number}: {homework.title}"
                    )
                    for question in homework.question_set.order_by("question_number", "created_at"):
                        lesson_chunks.append(
                            f"  Вопрос {question.question_number}: {question.text}"
                        )
                    for task in homework.task_set.order_by("task_number", "created_at"):
                        lesson_chunks.append(f"  Задание {task.task_number}: {task.text}")

                filename = f"course-{self.pk}-s{section.section_number}-l{lesson.lesson_number}.txt"
                files.append((filename, "\n".join(lesson_chunks)))

        return files

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Section(AbstractComponentModel, AutoIncrementMixin):
    section_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    section_number = models.PositiveIntegerField(verbose_name="Номер секции", blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="ID курса")
    title = models.CharField(max_length=120, verbose_name="Название секции")
    slug = models.SlugField(max_length=120, verbose_name="URL", blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title)

        self._generate_next_number(parent_field="course", number_field="section_number")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Секция"
        verbose_name_plural = "Секции"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["section_number"]),
        ]


class Lesson(AbstractComponentModel, AutoIncrementMixin):
    lesson_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    lesson_number = models.PositiveIntegerField(verbose_name="Номер урока", blank=True)
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, null=True, verbose_name="ID секции"
    )
    title = models.CharField(max_length=120, verbose_name="Название урока")
    slug = models.SlugField(max_length=120, verbose_name="URL", blank=True)
    document = models.TextField(
        blank=True,
        default="",
        verbose_name="JSON урока после подстановки URL (local:// → хранилище)",
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title)
        self._generate_next_number(parent_field="section", number_field="lesson_number")

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lesson_number"]),
        ]


class Homework(AbstractComponentModel, AutoIncrementMixin):
    homework_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    homework_number = models.PositiveIntegerField(
        verbose_name="Номер домашнего задания", blank=True
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, verbose_name="Название домашнего задания")
    slug = models.SlugField(max_length=120, verbose_name="URL", blank=True)
    deadline = models.DateTimeField(verbose_name="Дедлайн")
    max_points = models.PositiveIntegerField(default=0, verbose_name="Максимальный балл за домашку")

    def recalc_max_points(self):
        questions_total = self.question_set.aggregate(total=models.Sum("max_points"))["total"] or 0
        tasks_total = self.task_set.aggregate(total=models.Sum("max_points"))["total"] or 0
        Homework.objects.filter(pk=self.pk).update(max_points=questions_total + tasks_total)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title)
        self._generate_next_number(parent_field="lesson", number_field="homework_number")

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Домашнее задание"
        verbose_name_plural = "Домашние задания"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["homework_number"]),
        ]

    def __str__(self):
        return self.title


class Question(AbstractComponentModel, AutoIncrementMixin):
    question_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    question_number = models.PositiveIntegerField(verbose_name="Номер вопроса", blank=True)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, verbose_name="Текст вопроса")
    correct_ans = models.CharField(verbose_name="Правильный ответ на вопрос")
    answer_options = models.JSONField(verbose_name="Варианты ответов")
    max_points = models.PositiveIntegerField(
        default=1, verbose_name="Максимальное количество баллов за вопрос"
    )

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["question_number"]),
        ]

    def save(self, *args, **kwargs):
        self._generate_next_number(parent_field="homework", number_field="question_number")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class Task(AbstractComponentModel, AutoIncrementMixin):
    task_id = models.UUIDField(primary_key=True, verbose_name="id", default=uuid.uuid4)
    task_number = models.PositiveIntegerField(verbose_name="Номер задания", blank=True)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, verbose_name="Текст задания")
    max_points = models.PositiveIntegerField(
        default=0, verbose_name="Максимальное количество баллов за задание"
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["task_number"]),
        ]

    def save(self, *args, **kwargs):
        self._generate_next_number(parent_field="homework", number_field="task_number")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class CourseEnrollment(models.Model):
    SOURCE_PAYMENT = "payment"
    SOURCE_APPLICATION = "application"
    SOURCE_CHOICES = [
        (SOURCE_PAYMENT, "Оплата"),
        (SOURCE_APPLICATION, "Заявка"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_PAYMENT,
        verbose_name="Источник доступа",
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    access_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "course_enrollments"
        verbose_name = "Запись на курс"
        verbose_name_plural = "Записи на курсы"
        unique_together = ("user", "course")

    def __str__(self):
        return f"{self.user} → {self.course}"

    @property
    def is_active(self):
        from django.utils import timezone

        return timezone.now() < self.access_expires_at
