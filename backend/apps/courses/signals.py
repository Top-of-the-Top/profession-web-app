from apps.notifications.tasks import create_and_send_notification
from django.db.models.signals import pre_delete, pre_save, post_save
from django.dispatch import receiver

from .models import (
    DEFAULT_COURSE_IMAGE,
    Course,
    Homework,
    Question,
    Task
)
# Сигналы для курсов

@receiver(pre_save, sender=Course)
def handle_course_image_update(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if (old_instance.image and old_instance.image.name != DEFAULT_COURSE_IMAGE and
                instance.image and instance.image != old_instance.image):
            old_instance.image.delete(save=False)
    except sender.DoesNotExist:
        pass


@receiver(pre_delete, sender=Course)
def delete_course_image(sender, instance, **kwargs):
    if instance.image and instance.image.name != DEFAULT_COURSE_IMAGE:
        instance.image.delete(save=False)

@receiver(post_save, sender=Course)
def send_course_created_notification(sender, instance, created, **kwargs):
    if created:
        create_and_send_notification.delay(
            1,
            f"Курс «{instance.name}» создан!",
            "Новый курс доступен в системе."
        )


# Сигналы для домашних работ
@receiver(post_save, sender=Homework)
def send_homework_attached_notification(sender, instance, created, **kwargs):
    if created:
        create_and_send_notification.delay(
            1,
            f"Домашнее задание №{instance.pk} создано!",
            "Скорее приступайте к его выполнению!"
        )

    return None

# Сигналы для вопросов
@receiver(post_save, sender=Question)
def send_question_attached_notification(sender, instance, created, **kwargs):
    if created:
        create_and_send_notification.delay(
            1,
            f"Вопрос №{instance.pk} добавлен",
            "Готовы ответить на новый вопрос по домашнему заданию!"
        )
    return None

# Сигналы для заданий

@receiver(post_save, sender=Task)
def send_task_attached_notification(sender, instance, created, **kwargs):
    if created:
        create_and_send_notification.delay(
            1,
            f"Задание №{instance.pk} добавлено!",
            "Приступайте скорее!"
        )
    return None

