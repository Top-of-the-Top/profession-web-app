from django.db import models
from apps.courses.models import Course
from apps.users.models import User
from uuid import uuid4

class ChatSession(models.Model):

  chat_session_id = models.UUIDField(
    primary_key=True,
    verbose_name="id",
    default=uuid4
  )

  yandex_thread_id = models.CharField( # Это PK threadа который хранится в ресурсе яндекса
        max_length=255, 
        unique=True, 
        verbose_name="Yandex Thread ID",
        null=True, 
        blank=True
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
  created_at = models.DateTimeField(auto_now_add=True)

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
    verbose_name="Сообщение",
    null=False,
    blank=False,
  )
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    verbose_name = "Сообщение чата"
    verbose_name_plural = "Сообщения чата"
    ordering = ['created_at']

  def __str__(self):
    return f"{self.role}: {self.content[:40]}"
