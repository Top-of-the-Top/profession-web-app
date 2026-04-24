from enum import Enum 
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.users.models import User


class AttachmentType(Enum):
    DOCUMENT = "pdf"
    ARCHIVE = "zip"
    IMAGE = "png"
    TEXT = "txt"

class Attachment(models.Model):
    
    EXTENSION_CHOICES= [
        (AttachmentType.DOCUMENT, "Документ"), 
        (AttachmentType.ARCHIVE, "Архив"), 
        (AttachmentType.IMAGE, "Изображение"), 
        (AttachmentType.TEXT, "Текст"), 
    ]

    attachment_id = models.UUIDField(
        primary_key=True,
          default=uuid, 
          verbose_name="id"
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )

    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    url = models.CharField(
        max_length=100,
        verbose_name="URL файла в S3 хранилище"
    )

    name = models.CharField(
        max_length=40,
        verbose_name="Название файла"
    )
    size = models.PositiveIntegerField(
        verbose_name="Размер файла"
    )
    file_extension = models.CharField(
        max_length=40,
        choices=EXTENSION_CHOICES,
        verbose_name="Расширение"
    )
    
    def clean(self):
        limit = 1024*1024*10 

        if self.size > limit:
            raise ValidationError({
                'size': f'Файл слишком большой ({self.size} байт). Максимум: {limit} байт'
            })
        
    uploader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение'
        verbose_name_plural = 'Вложение'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        