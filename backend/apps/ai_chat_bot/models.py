from django.db import models
from apps.courses.models import Course
from apps.users.models import User
from uuid import uuid4
from django.dispatch import receiver
from django.utils import timezone

from django.db.models.signals import post_save

class TimestampedMixin(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Session(TimestampedMixin):

  session_id = models.UUIDField(
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


class Chat(TimestampedMixin):
   
    chat_id = models.UUIDField(
        primary_key=True,
        verbose_name="id",
        default=uuid4
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        verbose_name="Сессия чата",
    )

    title = models.CharField( 
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Заголовок чата"
    )

    class Meta:
      verbose_name = "Чаты"
      verbose_name_plural = "Сообщения чата"
      ordering = ['updated_at']
    

class Message(TimestampedMixin):
  ROLE_CHOICES = [
    ('user', 'Пользователь'),
    ('assistant', 'Ассистент'),
  ]

  message_id = models.UUIDField(
    primary_key=True,
    verbose_name="id",
    default=uuid4
  )

  chat = models.ForeignKey(
    Chat,
    on_delete=models.CASCADE,
    verbose_name="Чат",
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

  class Meta:
    verbose_name = "Сообщение чата"
    verbose_name_plural = "Сообщения чата"
    ordering = ['created_at']

  def __str__(self):
    return f"{self.role}: {self.content[:40]}"

@receiver(post_save, sender=Message)
def update_chat_on_message(sender, instance, **kwargs):
    chat = instance.chat
    chat.updated_at = timezone.now()
    if not chat.title:
        chat.title = instance.text[:100]

    chat.save(update_fields=['updated_at', 'title'])
    
