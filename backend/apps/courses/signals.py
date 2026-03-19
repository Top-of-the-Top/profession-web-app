from django.db.models.signals import pre_delete, pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from apps.notifications.tasks import send_course_notification, send_personal_notification
from .models import (
    DEFAULT_COURSE_IMAGE,
    Course,
    Homework,
    Question,
    Task
)



def notify_author(instance, action_name: str):
    """Отправляет подтверждение тому, кто внес изменения"""
    if instance.last_modified_by:
        send_personal_notification.delay(
            instance.last_modified_by.id,
            "Система",
            f"Объект '{instance}' успешно {action_name}."
        )



@receiver(pre_save, sender=Course)
def handle_course_image_update(sender, instance, **kwargs):
    if not instance.pk: return
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
def course_notification_signal(sender, instance, created, **kwargs):
    """Уведомление при создании или редактировании курса"""
    action = "создан" if created else "обновлен"

    notify_author(instance, action)

    if not created:
        send_course_notification.delay(
            instance.pk,
            f"Обновление курса: {instance.title}",
            "В материалы курса внесены изменения."
        )


@receiver(post_save, sender=Homework)
def homework_deadline_handler(sender, instance, created, **kwargs):
    """Уведомление о ДЗ и планирование дедлайнов"""
    course_id = instance.lesson_id.course_id_id
    action = "создано" if created else "изменено"

    notify_author(instance, action)

    title = f"{'Новое' if created else 'Изменено'} ДЗ: {instance.title}"
    send_course_notification.delay(
        course_id,
        title,
        f"Дедлайн: {instance.deadline.strftime('%d.%m %H:%M')}"
    )

    now = timezone.now()
    reminders = [
        (instance.deadline - timedelta(days=1), "До дедлайна осталось 24 часа!"),
        (instance.deadline - timedelta(hours=1), "Внимание! Дедлайн через 1 час!"),
    ]
    for eta, text in reminders:
        if eta > now:
            send_course_notification.apply_async(
                args=[course_id, f"Напоминание: {instance.title}", text],
                eta=eta,
                expires=instance.deadline
            )


@receiver(post_save, sender=Question)
def question_notification(sender, instance, created, **kwargs):
    """Уведомление о вопросе"""
    course_id = instance.homework_id.lesson_id.course_id_id
    action = "добавлен" if created else "отредактирован"

    notify_author(instance, action)

    title = "Новый вопрос добавлен" if created else "Вопрос обновлен"
    message = f"В ДЗ '{instance.homework_id.title}' {action} вопрос."
    send_course_notification.delay(course_id, title, message)


@receiver(post_save, sender=Task)
def task_notification(sender, instance, created, **kwargs):
    """Уведомление о задаче"""
    course_id = instance.homework_id.lesson_id.course_id_id
    action = "добавлена" if created else "изменена"

    notify_author(instance, action)

    title = "Новое задание добавлено" if created else "Задание отредактировано"
    message = f"В ДЗ '{instance.homework_id.title}' {action} задача: {instance.text[:30]}..."
    send_course_notification.delay(course_id, title, message)