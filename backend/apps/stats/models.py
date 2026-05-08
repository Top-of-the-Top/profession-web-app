import uuid

from django.conf import settings
from django.db import models

from apps.courses.models import Lesson, TimestampedMixin
from apps.webinars.models import Recording, Webinar


class WebinarAttendance(TimestampedMixin):
    attendance_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webinar_attendances",
    )
    webinar = models.ForeignKey(
        Webinar,
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    joined_at = models.DateTimeField(verbose_name="Подключился")
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Отключился",
    )
    watched_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name="Просмотрено секунд (агрегат)",
    )

    class Meta:
        verbose_name = "Посещение вебинара"
        verbose_name_plural = "Посещения вебинаров"
        ordering = ["-joined_at"]
        indexes = [
            models.Index(fields=["user", "webinar"]),
        ]


class RecordingView(TimestampedMixin):
    view_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recording_views",
    )
    recording = models.ForeignKey(
        Recording,
        on_delete=models.CASCADE,
        related_name="views",
    )
    watched_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name="Уникально просмотрено секунд",
    )
    last_position = models.PositiveIntegerField(
        default=0,
        verbose_name="Позиция остановки для resume",
    )

    class Meta:
        verbose_name = "Просмотр записи"
        verbose_name_plural = "Просмотры записей"
        unique_together = ("user", "recording")
        ordering = ["-updated_at"]


class LessonProgress(TimestampedMixin):
    progress_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )

    watched_ratio = models.FloatField(
        default=0.0,
        verbose_name="Доля просмотра от 0 до 1 (макс от live и записи)",
    )
    all_homeworks_submitted = models.BooleanField(
        default=False,
        verbose_name="Все ДЗ урока сданы",
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name="Урок пройден",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Когда впервые пройден",
    )

    class Meta:
        verbose_name = "Прогресс по уроку"
        verbose_name_plural = "Прогрессы по урокам"
        unique_together = ("user", "lesson")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_completed"]),
        ]
