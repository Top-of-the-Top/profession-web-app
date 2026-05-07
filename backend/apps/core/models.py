import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.users.models import User


class StorageBackend(models.TextChoices):
    S3 = "s3", "Yandex Object Storage"
    KINESCOPE = "kinescope", "Kinescope"
    EXTERNAL = "external", "Внешний URL"


class AssetStatus(models.TextChoices):
    PENDING = "pending", "Выдан presigned URL, загрузка не подтверждена"
    READY = "ready", "Готов к выдаче"
    DELETED = "deleted", "Физически удалён из хранилища"


class AssetVisibility(models.TextChoices):
    PRIVATE = "private", "Только владельцу / явным использованиям"
    COURSE_PAID = "course_paid", "Только купившим курс"
    PUBLIC = "public", "Публичный доступ"


class AssetRole(models.TextChoices):
    TASK_ATTACHMENT = "task_attachment", "Прикрепление к ответу на задание"
    HOMEWORK_MATERIAL = "homework_material", "Материал к домашке от автора"
    LESSON_BLOCK = "lesson_block", "Ассет внутри блока урока"
    COURSE_COVER = "course_cover", "Обложка курса"
    WEBINAR_RECORDING = "webinar_recording", "Запись вебинара"
    USER_AVATAR = "user_avatar", "Аватар пользователя"
    WHITEBOARD_PDF = "whiteboard_pdf", "PDF вебинарной доски"


class MediaAsset(models.Model):
    asset_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name="id",
    )

    storage_backend = models.CharField(
        max_length=20,
        choices=StorageBackend.choices,
        verbose_name="Хранилище",
    )
    storage_key = models.CharField(
        max_length=512,
        unique=True,
        verbose_name="Ключ в хранилище",
    )

    original_filename = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="Исходное имя файла",
    )
    mime_type = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="MIME-тип",
    )
    size_bytes = models.BigIntegerField(
        default=0,
        verbose_name="Размер (байт)",
    )
    status = models.CharField(
        max_length=20,
        choices=AssetStatus.choices,
        default=AssetStatus.PENDING,
        verbose_name="Статус",
    )

    visibility = models.CharField(
        max_length=20,
        choices=AssetVisibility.choices,
        default=AssetVisibility.PRIVATE,
        verbose_name="Видимость",
    )

    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_assets",
        verbose_name="Владелец",
    )
    ref_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Счётчик использований",
    )
    unreferenced_since = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Без использований с",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    committed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Подтверждён",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Физически удалён",
    )

    # Служебные данные бэкенда (например upload_link для Kinescope), не для публичного API
    storage_meta = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные хранилища",
    )

    class Meta:
        verbose_name = "Медиа-ассет"
        verbose_name_plural = "Медиа-ассеты"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(size_bytes__gte=0),
                name="asset_size_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["ref_count", "status"]),
            models.Index(fields=["storage_backend", "status"]),
            models.Index(fields=["status", "unreferenced_since"]),
        ]

    def __str__(self):
        return f"{self.storage_backend}:{self.storage_key} [{self.status}]"


class AssetUsage(models.Model):
    usage_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name="id",
    )
    asset = models.ForeignKey(
        MediaAsset,
        on_delete=models.CASCADE,
        related_name="usages",
        verbose_name="Ассет",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Тип сущности",
    )
    object_id = models.CharField(
        max_length=64,
        verbose_name="ID сущности",
    )
    role = models.CharField(
        max_length=32,
        choices=AssetRole.choices,
        verbose_name="Роль",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Использование ассета"
        verbose_name_plural = "Использования ассетов"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "content_type", "object_id", "role"],
                name="uniq_asset_usage",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["asset", "role"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.role}: {self.asset_id} -> {self.content_type_id}:{self.object_id}"
