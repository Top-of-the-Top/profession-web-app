import uuid

from django.conf import settings
from django.db import models

from apps.courses.models import TimestampedMixin


class Webinar(TimestampedMixin):
    PENDING_STATUS = "pending"
    LIVE_STATUS = "live"
    ENDED_STATUS = "ended"

    STATUS_CHOICES = [
        (PENDING_STATUS, "Ожидание"),
        (LIVE_STATUS, "В эфире"),
        (ENDED_STATUS, "Завершен"),
    ]

    webinar_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name="id",
    )
    lesson = models.OneToOneField(
        "courses.Lesson", on_delete=models.CASCADE, related_name="webinar", verbose_name="Урок"
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="started_webinars",
        verbose_name="Кто запустил",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING_STATUS,
        verbose_name="Статус",
    )

    agora_channel_name = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        verbose_name="Agora Channel Name",
    )

    whiteboard_room_uuid = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Whiteboard Room UUID",
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Начало",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Конец",
    )

    def save(self, *args, **kwargs):
        if not self.agora_channel_name:
            self.agora_channel_name = f"webinar-{str(self.lesson.lesson_id)[:8]}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Вебинар"
        verbose_name_plural = "Вебинары"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Вебинар: {self.lesson.title}"


class Recording(TimestampedMixin):
    RECORDING_STATUS = "recording"
    PROCESSING_STATUS = "processing"
    READY_STATUS = "ready"
    FAILED_STATUS = "failed"
    STATUS_CHOICES = [
        (RECORDING_STATUS, "Запись идет"),
        (PROCESSING_STATUS, "Обрабатывается"),
        (READY_STATUS, "Готово"),
        (FAILED_STATUS, "Ошибка"),
    ]

    KINESCOPE_UPLOAD_STATUS_CHOICES = [
        ("none", "Нет загрузки"),
        ("pending", "В очереди"),
        ("uploading", "Загружается"),
        ("processing", "Обрабатывается"),
        ("ready", "Готово"),
        ("failed", "Ошибка"),
    ]

    recording_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
    )
    webinar = models.ForeignKey(
        Webinar,
        on_delete=models.CASCADE,
        related_name="recordings",
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="started_recordings",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=RECORDING_STATUS,
    )

    resource_id = models.CharField(
        max_length=256,
        blank=True,
    )
    sid = models.CharField(
        max_length=256,
        blank=True,
    )
    recording_url = models.URLField(
        blank=True,
        verbose_name="Ссылка на запись",
    )
    whiteboard_pdf_url = models.URLField(
        blank=True,
        verbose_name="Ссылка на pdf доски",
    )

    kinescope_video_id = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Kenescope video id",
    )
    kinescope_upload_status = models.CharField(
        max_length=20,
        null=False,
        choices=KINESCOPE_UPLOAD_STATUS_CHOICES,
        default="none",
        verbose_name="Статут загрузки в кинескоп",
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Начало",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Конец",
    )

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="deleted_recordings",
    )

    class Meta:
        ordering = ["-started_at"]
