from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class CourseUpdatedEvent:
    course_id: UUID
    course_title: str
    with_email: bool = False


@dataclass
class AuthorActionEvent:
    user_id: int
    object_repr: str
    action: str
    with_email: bool = False


@dataclass
class NewHomeworkEvent:
    course_id: UUID
    course_title: str
    homework_title: str
    lesson_title: str
    deadline: datetime
    with_email: bool = True


@dataclass
class DeadlineChangedEvent:
    course_id: UUID
    course_title: str
    homework_title: str
    lesson_title: str
    deadline: datetime
    with_email: bool = True


@dataclass
class DeadlineReminderEvent:
    course_id: UUID
    homework_title: str
    deadline: datetime
    label: str
    with_email: bool = True


@dataclass
class HomeworkReviewedEvent:
    user_id: int
    homework_title: str
    grade: int | None
    attempt_id: UUID
    with_email: bool = True


@dataclass
class WebinarScheduledEvent:
    course_id: UUID
    title: str
    message: str
    webinar_id: UUID
    course_slug: str
    lesson_slug: str
    scheduled_at: str
    with_email: bool = False


@dataclass
class ApplicationStatusChangedEvent:
    user_id: int
    course_title: str
    new_status: str
    with_email: bool = False


@dataclass
class WebinarStartedEvent:
    course_id: UUID
    lesson_id: UUID
    course_slug: str
    lesson_slug: str
    course_title: str
    lesson_title: str
    webinar_id: UUID
    with_email: bool = True
