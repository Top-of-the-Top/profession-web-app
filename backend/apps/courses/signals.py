from django.db.models.signals import pre_delete, pre_save, post_save, post_delete, m2m_changed
from django.core.cache import cache
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from project.celery import app as celery_app
import hashlib

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
        title =  f"Обновление курса: {instance.title}",
        message =  "В материалы курса внесены изменения."
        notification = (
            course_id,
            title,
            message,
        )

        send_course_notification.delay(*notification)
        send_mass_course_email.delay(*notification)

def get_reminder_task_id_for_homework(homework_id, reminder_type, task_type):
    unique_key = f"homework_{homework_id}_reminder_{reminder_type}_{task_type}"
    return int(hashlib.md5(unique_key.encode()).hexdigest(), 16) % (10 ** 15)

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

    reminder_configs = [
        ('24h', timedelta(days=1), 'До дедлайна осталось 24 часа'),
        ('1h', timedelta(hours=1), 'До дедлайна остался 1 час'),
    ]
    deadline_changed = getattr(instance, '_deadline_changed', False)
    old_deadline = getattr(instance, '_old_deadline', None)

    if created or (deadline_changed and old_deadline):
        for r_type, delta, base_message in reminder_configs:
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


        return

@receiver(pre_save, sender=Homework)
def handle_pre_deadline_update(sender, instance, **kwargs):
    reminder_configs = [
        ('24h', timedelta(days=1), 'До дедлайна осталось 24 часа'),
        ('1h', timedelta(hours=1), 'До дедлайна остался 1 час'),
    ]

    deadline_changed = getattr(instance, '_deadline_changed', False)
    old_deadline = getattr(instance, '_old_deadline', None)

    if deadline_changed and old_deadline :
        for r_type, _, _ in reminder_configs:
            notif_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'notification')
            email_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'email')

            try:
                celery_app.control.revoke(notif_task_id, terminate=True)
                celery_app.control.revoke(email_task_id, terminate=True)
            except Exception:
                pass
        return
@receiver(pre_delete, sender=Homework)
def handle_pre_deadline_delete(sender, instance, **kwargs):

    reminder_configs = [
        ('24h', timedelta(days=1), 'До дедлайна осталось 24 часа'),
        ('1h', timedelta(hours=1), 'До дедлайна остался 1 час'),
    ]

    for r_type, _, _ in reminder_configs:
        notif_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'notification')
        email_task_id = get_reminder_task_id_for_homework(instance.pk, r_type, 'email')

        try:
            celery_app.control.revoke(notif_task_id, terminate=True)
            celery_app.control.revoke(email_task_id, terminate=True)
        except Exception:
            pass

    return

def get_reminder_task_id_for_lesson(lesson_id, reminder_type, task_type):
    unique_key = f"lesson_{lesson_id}_reminder_{reminder_type}_{task_type}"
    return int(hashlib.md5(unique_key.encode()).hexdigest(), 16) % (10 ** 15)

@receiver(pre_save, sender=Lesson)
def track_lesson_changes(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = Lesson.objects.get(pk=instance.pk)
        instance._date_time_changed = old.date_time != instance.date_time
        instance._old_date_time = old.date_time
    except Lesson.DoesNotExist:
        pass

@receiver(post_save, sender=Lesson)
def handle_lesson_reminders(sender, instance, created, **kwargs):
    cours = instance.section.course
    now = timezone.now()

    notify_author(instance, 'создан' if created else 'изменен')

    reminder_configs = [
        ('24h', timedelta(days=1), 'До занятия остался 24 часа'),
        ('1h', timedelta(hours=1), 'До занятия остался 1 час'),
    ]

    date_time_changed = getattr(instance, '_date_time_changed', False)
    old_time_date = getattr(instance, '_old_date_time', None)

    if created or (date_time_changed and old_time_date):
        for r_type, delta, base_message in reminder_configs:
            eta = instance.date_time - delta

            if eta > now:
                notif_task_id = get_reminder_task_id_for_lesson(instance.pk, r_type, 'notification')
                email_task_id = get_reminder_task_id_for_lesson(instance.pk, r_type, 'email')

                title = f'Напоминание: {instance.title}'
                message = (
                    f'{base_message}.\n'
                    f'Урок: "{instance.title}"\n'
                    f'Дата проведения: {instance.date_time.strftime("%d.%m %H:%M")}'
                )

                send_course_notification.apply_async(
                    args=[cours, title, message],
                    eta=eta,
                    task_id=notif_task_id
                )

                send_mass_course_email.apply_async(
                    args=[cours, title, message],
                    eta=eta,
                    task_id=email_task_id
                )

        return

@receiver(pre_save, sender=Lesson)
def handle_lesson_update(sender, instance, **kwargs):
    reminder_configs = [
        ('24h', timedelta(days=1), 'До занятия остался 24 часа'),
        ('1h', timedelta(hours=1), 'До занятия остался 1 час'),
    ]

    date_time_changed = getattr(instance, '_date_time_changed', False)
    old_time_date = getattr(instance, '_old_date_time', None)

    if date_time_changed and old_time_date :
        for r_type, _, _ in reminder_configs:
            notif_task_id = get_reminder_task_id_for_lesson(instance.pk, r_type, 'notification')
            email_task_id = get_reminder_task_id_for_lesson(instance.pk, r_type, 'email')

            try:
                celery_app.control.revoke(notif_task_id, terminate=True)
                celery_app.control.revoke(email_task_id, terminate=True)
            except Exception:
                pass
        return
@receiver(pre_delete, sender=Lesson)
def handle_pre_lesson_delete(sender, instance, **kwargs):

    reminder_configs = [
        ('24h', timedelta(days=1), 'До занятия остался 24 часа'),
        ('1h', timedelta(hours=1), 'До занятия остался 1 час'),
    ]

    for r_type, _, _ in reminder_configs:
        notif_task_id = get_reminder_task_id_for_lesson(instance.pk, r_type, 'notification')
        email_task_id = get_reminder_task_id_for_lesson(instance.pk, r_type, 'email')

        try:
            celery_app.control.revoke(notif_task_id, terminate=True)
            celery_app.control.revoke(email_task_id, terminate=True)
        except Exception:
            pass

    return
@receiver(post_save, sender=Course)
@receiver(post_delete, sender=Course)
def invalidate_course_cache(sender, instance, **kwargs):
    """Инвалидация кэша курсов при создании/обновлении/удалении курса"""
    try:
        cache_keys = [
            'course_list',
            'courses_list',
        ]

        for key in cache_keys:
            cache.delete(key)

        if hasattr(instance, 'slug') and instance.slug:
            detail_key = f'course_detail_{instance.slug}'
            cache.delete(detail_key)

        if not kwargs.get('created', False) and hasattr(instance, 'slug'):
            old_slug = getattr(instance, '_old_slug', None)
            if old_slug and old_slug != instance.slug:
                old_detail_key = f'course_detail_{old_slug}'
                cache.delete(old_detail_key)

    except Exception as e:
        pass

@receiver(m2m_changed, sender=Course.authors.through)
def invalidate_course_cache_on_authors_change(sender, instance, action, **kwargs):
    """Инвалидация кэша при изменении авторов курса"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        try:
            cache.delete(f'course_detail_{instance.slug}')
            cache.delete('course_list')
            cache.delete('courses_list')
        except Exception as e:
            pass
@receiver(post_save, sender=Section)
@receiver(post_delete, sender=Section)
def invalidate_section_cache(sender, instance, **kwargs):
    """Инвалидация кэша секций при изменениях"""
    try:
        course_slug = instance.course_id.slug if instance.course_id else None

        if course_slug:
            sections_key = f'sections_list_{course_slug}'
            cache.delete(sections_key)

            if hasattr(instance, 'slug') and instance.slug:
                detail_key = f'section_detail_{instance.slug}'
                cache.delete(detail_key)

            cache.delete(f'course_detail_{course_slug}')
            cache.delete('course_list')
            cache.delete('courses_list')

    except Exception as e:
        pass
@receiver(post_save, sender=Lesson)
@receiver(post_delete, sender=Lesson)
def invalidate_lesson_cache(sender, instance, **kwargs):
    """Инвалидация кэша уроков при изменениях"""
    try:
        section_slug = instance.section_id.slug if instance.section_id else None
        course_slug = instance.section_id.course_id.slug if instance.section_id and instance.section_id.course_id else None

        if section_slug:
            lessons_key = f'lessons_list_{section_slug}'
            cache.delete(lessons_key)

            if hasattr(instance, 'slug') and instance.slug:
                detail_key = f'lesson_detail_{instance.slug}'
                cache.delete(detail_key)

        if course_slug:
            cache.delete(f'course_detail_{course_slug}')
            cache.delete(f'sections_list_{course_slug}')
            cache.delete('course_list')
            cache.delete('courses_list')

    except Exception as e:
        pass
@receiver(post_save, sender=Homework)
@receiver(post_delete, sender=Homework)
def invalidate_homework_cache(sender, instance, **kwargs):
    """Инвалидация кэша домашних заданий при изменениях"""
    try:
        lesson_slug = instance.lesson_id.slug if instance.lesson_id else None
        section_slug = instance.lesson_id.section_id.slug if instance.lesson_id and instance.lesson_id.section_id else None
        course_slug = instance.lesson_id.section_id.course_id.slug if instance.lesson_id and instance.lesson_id.section_id and instance.lesson_id.section_id.course_id else None

        if lesson_slug:
            homeworks_key = f'homeworks_list_{lesson_slug}'
            cache.delete(homeworks_key)

            if hasattr(instance, 'slug') and instance.slug:
                detail_key = f'homework_detail_{instance.slug}'
                cache.delete(detail_key)

        if course_slug:
            cache.delete(f'course_detail_{course_slug}')
            cache.delete(f'sections_list_{course_slug}')

            if section_slug:
                cache.delete(f'lessons_list_{section_slug}')

    except Exception as e:
        pass
@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_task_cache(sender, instance, **kwargs):
    """Инвалидация кэша задач при изменениях"""
    try:
        homework_slug = instance.homework_id.slug if instance.homework_id else None
        lesson_slug = instance.homework_id.lesson_id.slug if instance.homework_id and instance.homework_id.lesson_id else None

        if homework_slug:
            tasks_key = f'tasks_list_{homework_slug}'
            cache.delete(tasks_key)

            if hasattr(instance, 'slug') and instance.slug:
                detail_key = f'task_detail_{instance.slug}'
                cache.delete(detail_key)

        if lesson_slug:
            cache.delete(f'homeworks_list_{lesson_slug}')

    except Exception as e:
        pass
@receiver(post_save, sender=Question)
@receiver(post_delete, sender=Question)
def invalidate_question_cache(sender, instance, **kwargs):
    """Инвалидация кэша вопросов при изменениях"""
    try:
        homework_slug = instance.homework_id.slug if instance.homework_id else None

        if homework_slug:
            questions_key = f'questions_list_{homework_slug}'
            cache.delete(questions_key)

            if hasattr(instance, 'slug') and instance.slug:
                detail_key = f'question_detail_{instance.slug}'
                cache.delete(detail_key)


    except Exception as e:
        pass
@receiver(post_save, sender=PurchasedCourse)
@receiver(post_delete, sender=PurchasedCourse)
def invalidate_purchased_course_cache(instance, **kwargs):
    """Инвалидация кэша купленных курсов при изменениях"""
    try:
        user_id = instance.user_id if instance.user_id else None

        if user_id:
            purchased_key = f'purchased_courses_user_{user_id}'
            cache.delete(purchased_key)

            if hasattr(instance, 'course') and instance.course:
                access_key = f'course_access_user_{user_id}_course_{instance.course.slug}'
                cache.delete(access_key)


    except Exception as e:
        pass