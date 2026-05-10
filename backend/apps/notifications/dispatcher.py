from typing import Callable

from django.conf import settings

from .events import (
    ApplicationStatusChangedEvent,
    AuthorActionEvent,
    CourseUpdatedEvent,
    DeadlineChangedEvent,
    DeadlineReminderEvent,
    HomeworkReviewedEvent,
    NewHomeworkEvent,
    WebinarScheduledEvent,
    WebinarStartedEvent,
)
from .tasks import (
    send_course_notification,
    send_mass_course_email,
    send_personal_notification,
    send_single_email,
    send_webinar_scheduled_notification,
    send_webinar_started_notification,
)

_APPLICATION_STATUS_TITLES = {
    "approved": "Заявка на курс одобрена",
    "rejected": "Заявка на курс отклонена",
}

_APPLICATION_STATUS_MESSAGES = {
    "approved": 'Ваша заявка на курс "{course_title}" одобрена. Курс доступен на главной странице.',
    "rejected": 'Ваша заявка на курс "{course_title}" отклонена.',
}


class NotificationDispatcher:
    def __init__(self) -> None:
        self._registry: dict[type, Callable] = {}

    def register(self, event_type: type) -> Callable:
        def decorator(handler: Callable) -> Callable:
            self._registry[event_type] = handler
            return handler

        return decorator

    def dispatch(self, event) -> None:
        handler = self._registry.get(type(event))
        if handler is None:
            raise NotImplementedError(f"Нет обработчика для события {type(event).__name__}")
        handler(event)


dispatcher = NotificationDispatcher()


@dispatcher.register(CourseUpdatedEvent)
def _(event: CourseUpdatedEvent) -> None:
    title = f"Обновление курса: {event.course_title}"
    message = "В материалы курса внесены изменения."
    send_course_notification.delay(event.course_id, title, message)
    if event.with_email:
        send_mass_course_email.delay(event.course_id, title, message)


@dispatcher.register(AuthorActionEvent)
def _(event: AuthorActionEvent) -> None:
    title = "Система"
    message = f"Объект '{event.object_repr}' успешно {event.action}."
    send_personal_notification.delay(event.user_id, title, message)
    if event.with_email:
        send_single_email.delay(event.user_id, title, message)


@dispatcher.register(NewHomeworkEvent)
def _(event: NewHomeworkEvent) -> None:
    deadline_str = event.deadline.strftime("%d.%m %H:%M")
    title = f"Новое домашнее задание: {event.homework_title}"
    message = (
        f'По курсу "{event.course_title}" добавлено новое задание.\n'
        f"Дедлайн: {deadline_str}.\n"
        f"Урок: {event.lesson_title}."
    )
    send_course_notification.delay(event.course_id, title, message)
    if event.with_email:
        send_mass_course_email.delay(event.course_id, title, message)


@dispatcher.register(DeadlineChangedEvent)
def _(event: DeadlineChangedEvent) -> None:
    deadline_str = event.deadline.strftime("%d.%m %H:%M")
    title = f"Дедлайн домашнего задания перенесён: {event.homework_title}"
    message = (
        f'В курсе "{event.course_title}" обновлен дедлайн домашнего задания "{event.homework_title}"\n'
        f"Новый дедлайн: {deadline_str}.\n"
        f"Урок: {event.lesson_title}."
    )
    send_course_notification.delay(event.course_id, title, message)
    if event.with_email:
        send_mass_course_email.delay(event.course_id, title, message)


@dispatcher.register(DeadlineReminderEvent)
def _(event: DeadlineReminderEvent) -> None:
    title = f"Напоминание: {event.homework_title}"
    message = (
        f"{event.label}.\n"
        f'Задание: "{event.homework_title}"\n'
        f"Дедлайн: {event.deadline.strftime('%d.%m %H:%M')}"
    )
    send_course_notification.delay(event.course_id, title, message)
    if event.with_email:
        send_mass_course_email.delay(event.course_id, title, message)


@dispatcher.register(HomeworkReviewedEvent)
def _(event: HomeworkReviewedEvent) -> None:
    grade_text = event.grade if event.grade is not None else "—"
    title = f"Домашнее задание «{event.homework_title}» проверено"
    message = (
        f"Ваше домашнее задание «{event.homework_title}» проверено.\n\n"
        f"Оценка: {grade_text}\n\n"
        f"Комментарии к заданиям смотрите в личном кабинете.\n"
        f"{settings.FRONTEND_HOST.rstrip('/')}/homeworks/{event.attempt_id}"
    )
    send_personal_notification.delay(event.user_id, title, message)
    if event.with_email:
        send_single_email.delay(event.user_id, title, message)


@dispatcher.register(WebinarScheduledEvent)
def _(event: WebinarScheduledEvent) -> None:
    send_webinar_scheduled_notification.delay(
        event.course_id,
        event.title,
        event.message,
        event.webinar_id,
        event.course_slug,
        event.lesson_slug,
        event.scheduled_at,
    )
    if event.with_email:
        send_mass_course_email.delay(event.course_id, event.title, event.message)


@dispatcher.register(WebinarStartedEvent)
def _(event: WebinarStartedEvent) -> None:
    send_webinar_started_notification.delay(
        event.course_id,
        event.lesson_id,
        event.course_slug,
        event.lesson_slug,
        event.course_title,
        event.lesson_title,
        event.webinar_id,
    )


@dispatcher.register(ApplicationStatusChangedEvent)
def _(event: ApplicationStatusChangedEvent) -> None:
    title = _APPLICATION_STATUS_TITLES.get(event.new_status, "Статус заявки изменён")
    message = _APPLICATION_STATUS_MESSAGES.get(
        event.new_status, f'Статус вашей заявки на курс "{event.course_title}" изменён.'
    ).format(course_title=event.course_title)
    send_personal_notification.delay(event.user_id, title, message)
    if event.with_email:
        send_single_email.delay(event.user_id, title, message)
