import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.users.api.utils.crypto_utils import decrypt_data
from apps.users.models import User

from .models import Notification
from .rabbit import publish_event

logger = logging.getLogger(__name__)


@shared_task
def publish_event_async(routing_key, payload):
    publish_event(routing_key=routing_key, payload=payload)


@shared_task
def send_course_notification(course_id, title, message):
    notif = Notification.objects.create(
        course_id=course_id,
        title=title,
        notification_type=Notification.COURSE,
        message=message,
    )
    publish_event(
        routing_key=f"course.{course_id}",
        payload={
            "id": notif.id,
            "type": "course_update",
            "title": title,
            "message": message,
            "created_at": timezone.now().isoformat(),
        },
    )


@shared_task
def send_personal_notification(user_id, title, message):
    notif = Notification.objects.create(
        user_id=user_id,
        title=title,
        notification_type=Notification.PERSONAL,
        message=message,
    )
    publish_event(
        routing_key=f"user.{user_id}",
        payload={
            "id": notif.id,
            "type": "personal",
            "title": title,
            "message": message,
            "created_at": timezone.now().isoformat(),
        },
    )


@shared_task
def send_system_notification(title, message):
    notif = Notification.objects.create(
        title=title,
        notification_type=Notification.SYSTEM,
        message=message,
    )
    publish_event(
        routing_key="system.all",
        payload={
            "id": notif.id,
            "type": "system",
            "title": title,
            "message": message,
            "created_at": timezone.now().isoformat(),
        },
    )


@shared_task
def send_single_email(user_id, subject, message):
    try:
        user = User.objects.get(pk=user_id)
        user_email = decrypt_data(user.email_cipher)
        if user_email:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
            )
    except User.DoesNotExist:
        logger.error("Пользователь %s не найден", user_id)
    except Exception as e:
        logger.error("Ошибка отправки письма пользователю %s: %s", user_id, e)


@shared_task
def send_mass_course_email(course_id, subject, message):
    user_ids = (
        User.objects.filter(purchased_courses__course_id=course_id)
        .distinct()
        .values_list("id", flat=True)
    )
    for user_id in user_ids:
        send_single_email.delay(user_id, subject, message)


@shared_task
def send_mass_system_email(subject, message):
    user_ids = User.objects.values_list("id", flat=True)
    for user_id in user_ids:
        send_single_email.delay(user_id, subject, message)


@shared_task
def send_webinar_scheduled_notification(
    course_id,
    title,
    message,
    webinar_id,
    course_slug,
    lesson_slug,
    scheduled_at,
):
    notif = Notification.objects.create(
        course_id=course_id,
        title=title,
        notification_type=Notification.COURSE,
        message=message,
    )
    publish_event(
        routing_key=f"course.{course_id}",
        payload={
            "id": notif.id,
            "type": "webinar_scheduled",
            "title": title,
            "message": message,
            "created_at": notif.created_at.isoformat(),
            "webinar_id": str(webinar_id),
            "course_id": str(course_id),
            "course_slug": course_slug,
            "lesson_slug": lesson_slug,
            "scheduled_at": scheduled_at,
        },
    )


@shared_task
def send_webinar_started_notification(
    course_id,
    lesson_id,
    course_slug,
    lesson_slug,
    course_title,
    lesson_title,
    webinar_id,
):
    title = "Преподаватель начал вебинар"
    message = f"Идет прямой эфир по уроку «{lesson_title}» курса «{course_title}». Присоединяйтесь!"

    notif = Notification.objects.create(
        course_id=course_id,
        title=title,
        notification_type=Notification.COURSE,
        message=message,
    )
    publish_event(
        routing_key=f"course.{course_id}",
        payload={
            "id": notif.id,
            "type": "webinar_started",
            "title": title,
            "message": message,
            "created_at": notif.created_at.isoformat(),
            "webinar_id": str(webinar_id),
            "course_id": course_id,
            "lesson_id": lesson_id,
            "course_slug": course_slug,
            "lesson_slug": lesson_slug,
        },
    )

    user_ids = (
        User.objects.filter(purchased_courses__course_id=course_id)
        .distinct()
        .values_list("id", flat=True)
    )
    for user_id in user_ids:
        send_single_email.delay(user_id, title, message)
