from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Message


@receiver(post_save, sender=Message)
def update_chat_on_message(sender, instance, **kwargs):
    chat = instance.chat
    chat.updated_at = timezone.now()
    if not chat.title:
        chat.title = instance.content[:25]

    chat.save(update_fields=["updated_at", "title"])
