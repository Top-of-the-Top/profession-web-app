from django.db import models
from pgvector.django import VectorField
from apps.courses.models import Course, Lesson
from apps.users.models import User
from uuid import uuid4

class Chunk(models.Model):

  chunk_id = models.UUIDField(
    primary_key=True,
    verbose_name="id",
    default=uuid4
  )

  course = models.ForeignKey( # Наверное можно убрать, но пока пусть будет
    Course, 
    on_delete=models.CASCADE,
    verbose_name="Курс",
    null=False,
  )

  lesson = models.ForeignKey(
    Lesson,
    on_delete=models.CASCADE,
    verbose_name="Урок",
    null=False,
  )

  content = models.TextField(
    max_length=1000,
    verbose_name="Контент",
    null=False,
    blank=False,
  )

  embedding = VectorField(
    verbose_name="Эмбеддинг",
    dimensions=1536,
    null=False,
    blank=False,
  )

  created_at = models.DateTimeField(
    auto_now_add=True,
    verbose_name="Дата создания",
  )

  class Meta:
    verbose_name = "Чанк"
    verbose_name_plural = "Чанки"
    ordering = ['-created_at']
    indexes = [
      models.Index(fields=['embedding']),
    ]
  
class ChatSession(models.Model):

  chat_session_id = models.UUIDField(
    primary_key=True,
    verbose_name="id",
    default=uuid4
  )

  user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    verbose_name="Пользователь",
  )

  course = models.ForeignKey(
    Course,
    on_delete=models.CASCADE,
    verbose_name="Курс",
  )

  class Meta:
    verbose_name = "Сессия чата"
    verbose_name_plural = "Сессии чата"
    ordering = ['-created_at']
    indexes = [
      models.Index(fields=['user', 'course']),
    ]

  def __str__(self):
    return f"{self.user} - {self.course}"


class ChatMessage(models.Model):
  ROLE_CHOICES = [
    ('user', 'Пользователь'),
    ('assistant', 'Ассистент'),
  ]

  chat_message_id = models.UUIDField(
    primary_key=True,
    verbose_name="id",
    default=uuid4
  )

  chat_session = models.ForeignKey(
    ChatSession,
    on_delete=models.CASCADE,
    verbose_name="Сессия чата",
  )

  role = models.CharField(
    max_length=10,
    choices=ROLE_CHOICES,
    verbose_name="Роль",
    null=False,
    blank=False,
  )

  content = models.TextField(
    max_length=1000,
    verbose_name="Контент",
    null=False,
    blank=False,
  )
