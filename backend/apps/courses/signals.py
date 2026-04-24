from django.db.models.signals import pre_delete, pre_save, post_save, post_delete, m2m_changed
from django.core.cache import cache, caches
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from project.celery import app as celery_app
import hashlib
import logging
logger = logging.getLogger(__name__)

from apps.notifications.tasks import (
    send_course_notification,
    send_personal_notification,
    send_single_email,
    send_mass_course_email,
    send_mass_system_email
)

from .models import (
    DEFAULT_COURSE_IMAGE,
    Course,
    Section,
    Lesson,
    Homework,
    Task,
    Question,
    PurchasedCourse
)
REMINDER_CONFIGS = [
    ('24h', timedelta(days=1), 'До дедлайна осталось 24 часа'),
    ('1h', timedelta(hours=1), 'До дедлайна остался 1 час'),
]


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

def notify_author(instance, action_name: str):
    if instance.last_modified_by:
        send_personal_notification.delay(
            instance.last_modified_by.id,
            "Система",
            f"Объект '{instance}' успешно {action_name}."
        )


@receiver(post_save, sender=Course)
def course_notification_signal(sender, instance, created, **kwargs):
    action = "создан" if created else "обновлен"

    notify_author(instance, action)

    if not created:
        course_id = instance.pk
        title = f"Обновление курса: {instance.title}"
        message = "В материалы курса внесены изменения."
        notification = (
            course_id,
            title,
            message,
        )

        send_course_notification.delay(*notification)
        send_mass_course_email.delay(*notification)


def get_reminder_task_id_for_homework(homework_id, reminder_type, task_type):
    unique_key = f"homework_{homework_id}_reminder_{reminder_type}_{task_type}"
    return str(int(hashlib.md5(unique_key.encode()).hexdigest(), 16) % (10 ** 15))


@receiver(pre_save, sender=Homework)
def track_homework_changes(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = Homework.objects.get(pk=instance.pk)
        instance._deadline_changed = old.deadline != instance.deadline
        instance._old_deadline = old.deadline
    except Homework.DoesNotExist:
        pass


@receiver(post_save, sender=Homework)
def homework_notification(sender, instance, created, **kwargs):

    course = instance.lesson.section.course
    deadline_str = instance.deadline.strftime('%d.%m %H:%M')

    notify_author(instance, 'прикреплено' if created else 'изменено')

    if created and instance.deadline > timezone.now():
        title = f'Новое домашнее задание: {instance.title}'
        message = (
            f'По курсу "{course.title}" добавлено новое задание.\n'
            f'Дедлайн: {deadline_str}.\n'
            f'Урок: {instance.lesson.title}.'
        )
        send_course_notification.delay(course.course_id, title, message)
        send_mass_course_email.delay(course.course_id, title, message)
    elif instance.deadline > timezone.now():
        deadline_changed = getattr(instance, '_deadline_changed', False)
        old_deadline = getattr(instance, '_old_deadline', None)

        if deadline_changed and old_deadline:

            title = f'Дедлайн домашнего задания перенесён: {instance.title}'
            message = (
                f'В курсе "{course.title}" обновлен дедлайн домашнего задания "{instance.title}"\n'
                f'Новый дедлайн: {deadline_str}.\n'
                f'Урок: {instance.lesson.title}.'
            )

            send_course_notification.delay(course.course_id, title, message)
            send_mass_course_email.delay(course.course_id, title, message)


@receiver(post_save, sender=Homework)
def handle_deadline_reminders(sender, instance, created, **kwargs):
    course = instance.lesson.section.course
    now = timezone.now()

    deadline_changed = getattr(instance, '_deadline_changed', False)
    old_deadline = getattr(instance, '_old_deadline', None)

    if created or (deadline_changed and old_deadline):
        for r_type, delta, base_message in REMINDER_CONFIGS:
            eta = instance.deadline - delta

            if eta > now:
                notif_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'notification')
                email_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'email')

                title = f'Напоминание: {instance.title}'
                message = (
                    f'{base_message}.\n'
                    f'Задание: "{instance.title}"\n'
                    f'Дедлайн: {instance.deadline.strftime("%d.%m %H:%M")}'
                )

                send_course_notification.apply_async(
                    args=[course.course_id, title, message],
                    eta=eta,
                    task_id=notif_task_id
                )

                send_mass_course_email.apply_async(
                    args=[course.course_id, title, message],
                    eta=eta,
                    task_id=email_task_id
                )


@receiver(pre_save, sender=Homework)
def handle_pre_deadline_update(sender, instance, **kwargs):
    deadline_changed = getattr(instance, '_deadline_changed', False)
    old_deadline = getattr(instance, '_old_deadline', None)

    if deadline_changed and old_deadline :
        for r_type, _, _ in REMINDER_CONFIGS:
            notif_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'notification')
            email_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'email')

            try:
                celery_app.control.revoke(notif_task_id, terminate=True)
                celery_app.control.revoke(email_task_id, terminate=True)
            except Exception as exc:
                logger.warning("Не удалось отменить celery-задачу для homework=%s: %s", instance.pk, exc)


@receiver(pre_delete, sender=Homework)
def handle_pre_deadline_delete(sender, instance, **kwargs):
    for r_type, _, _ in REMINDER_CONFIGS:
        notif_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'notification')
        email_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'email')

        try:
            celery_app.control.revoke(notif_task_id, terminate=True)
            celery_app.control.revoke(email_task_id, terminate=True)
        except Exception as exc:
            logger.warning("Не удалось отменить celery-задачу для homework=%s: %s", instance.pk, exc)


def get_reminder_task_id_for_lesson(lesson_id, reminder_type, task_type):
    unique_key = f"lesson_{lesson_id}_reminder_{reminder_type}_{task_type}"
    return str(int(hashlib.md5(unique_key.encode()).hexdigest(), 16) % (10 ** 15))


from .api.utils.cache_utils import (
    invalidate_on_course_model_change,
    invalidate_on_homework_tree_change,
    invalidate_on_lesson_model_change,
    invalidate_on_section_model_change,
    purchased_courses_cache_key,
)


@receiver((pre_save, pre_delete), sender=Course)
def invalidate_cold_course_cache(sender, instance, **kwargs):
    invalidate_on_course_model_change(instance.slug)


@receiver((pre_save, pre_delete), sender=Section)
def invalidate_cold_section_cache(sender, instance, **kwargs):
    course_slug = instance.course.slug
    invalidate_on_section_model_change(course_slug, instance.slug)


@receiver((pre_save, pre_delete), sender=Lesson)
def invalidate_cold_lesson_cache(sender, instance, **kwargs):
    section = instance.section
    if section is None:
        return
    course_slug = section.course.slug
    invalidate_on_lesson_model_change(course_slug, instance.slug)


@receiver((pre_save, pre_delete), sender=Homework)
def invalidate_cold_homework_cache(sender, instance, **kwargs):
    lesson = instance.lesson
    section = lesson.section
    if section is None:
        return
    course_slug = section.course.slug
    invalidate_on_homework_tree_change(course_slug, lesson.slug, instance.slug)


@receiver((pre_save, pre_delete), sender=Task)
def invalidate_cold_task_cache(sender, instance, **kwargs):
    hw = instance.homework
    lesson = hw.lesson
    section = lesson.section
    if section is None:
        return
    course_slug = section.course.slug
    invalidate_on_homework_tree_change(course_slug, lesson.slug, hw.slug)


@receiver((pre_save, pre_delete), sender=Question)
def invalidate_cold_question_cache(sender, instance, **kwargs):
    hw = instance.homework
    lesson = hw.lesson
    section = lesson.section
    if section is None:
        return
    course_slug = section.course.slug
    invalidate_on_homework_tree_change(course_slug, lesson.slug, hw.slug)


@receiver((pre_save, pre_delete), sender=PurchasedCourse)
def invalidate_default_purchased_cache(sender, instance, **kwargs):
    caches["default"].delete(purchased_courses_cache_key(instance.user_id))
