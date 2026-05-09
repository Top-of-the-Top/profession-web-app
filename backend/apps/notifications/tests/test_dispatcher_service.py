from dataclasses import dataclass
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.notifications.dispatcher import dispatcher
from apps.notifications.events import (
    AuthorActionEvent,
    CourseUpdatedEvent,
    DeadlineReminderEvent,
    HomeworkReviewedEvent,
    WebinarScheduledEvent,
    WebinarStartedEvent,
)


@dataclass
class _UnhandledStubEvent:
    pass


class DispatcherEnqueueTasksTests(SimpleTestCase):
    def _patch_delays(self):
        targets = (
            "apps.notifications.tasks.send_course_notification.delay",
            "apps.notifications.tasks.send_mass_course_email.delay",
            "apps.notifications.tasks.send_personal_notification.delay",
            "apps.notifications.tasks.send_single_email.delay",
            "apps.notifications.tasks.send_webinar_scheduled_notification.delay",
            "apps.notifications.tasks.send_webinar_started_notification.delay",
        )
        mocks = {}
        patchers = []
        for path in targets:
            p = patch(path)
            patchers.append(p)
            mocks[path.split(".")[-2]] = p.start()
        self.addCleanup(lambda: [x.stop() for x in reversed(patchers)])
        return mocks

    def test_course_updated_without_email_only_course_notification_delay(self):
        mocks = self._patch_delays()
        cid = uuid4()
        dispatcher.dispatch(
            CourseUpdatedEvent(course_id=cid, course_title="Курс А", with_email=False)
        )
        mocks["send_course_notification"].assert_called_once()
        mocks["send_mass_course_email"].assert_not_called()

    def test_deadline_reminder_with_email_course_and_mass_delays(self):
        mocks = self._patch_delays()
        cid = uuid4()
        deadline = datetime(2026, 6, 1, 12, 0, 0)
        dispatcher.dispatch(
            DeadlineReminderEvent(
                course_id=cid,
                homework_title="ДЗ",
                deadline=deadline,
                label="За сутки",
                with_email=True,
            )
        )
        mocks["send_course_notification"].assert_called_once()
        mocks["send_mass_course_email"].assert_called_once()

    def test_author_action_with_email_personal_and_single_email_delays(self):
        mocks = self._patch_delays()
        dispatcher.dispatch(
            AuthorActionEvent(
                user_id=42,
                object_repr="Урок",
                action="сохранён",
                with_email=True,
            )
        )
        mocks["send_personal_notification"].assert_called_once()
        mocks["send_single_email"].assert_called_once()

    def test_webinar_scheduled_delays_and_optional_mass_email(self):
        mocks = self._patch_delays()
        cid, wid = uuid4(), uuid4()
        dispatcher.dispatch(
            WebinarScheduledEvent(
                course_id=cid,
                title="Вебинар",
                message="Скоро",
                webinar_id=wid,
                course_slug="c",
                lesson_slug="l",
                scheduled_at="2026-06-01T18:00:00",
                with_email=True,
            )
        )
        mocks["send_webinar_scheduled_notification"].assert_called_once()
        mocks["send_mass_course_email"].assert_called_once()

    def test_webinar_started_only_started_notification_delay(self):
        mocks = self._patch_delays()
        cid, lid, wid = uuid4(), uuid4(), uuid4()
        dispatcher.dispatch(
            WebinarStartedEvent(
                course_id=cid,
                lesson_id=lid,
                course_slug="c",
                lesson_slug="l",
                course_title="Курс",
                lesson_title="Урок",
                webinar_id=wid,
                with_email=True,
            )
        )
        mocks["send_webinar_started_notification"].assert_called_once()
        mocks["send_mass_course_email"].assert_not_called()

    def test_homework_reviewed_passes_attempt_and_grade_into_messages(self):
        mocks = self._patch_delays()
        aid = uuid4()
        dispatcher.dispatch(
            HomeworkReviewedEvent(
                user_id=7,
                homework_title="Лаба",
                grade=10,
                attempt_id=aid,
                with_email=False,
            )
        )
        mocks["send_personal_notification"].assert_called_once()
        _args = mocks["send_personal_notification"].call_args[0]
        self.assertEqual(_args[0], 7)
        self.assertIn("Лаба", _args[1])
        self.assertIn("10", _args[2])
        self.assertIn(str(aid), _args[2])
        mocks["send_single_email"].assert_not_called()

    def test_dispatch_unregistered_event_raises(self):
        with self.assertRaises(NotImplementedError):
            dispatcher.dispatch(_UnhandledStubEvent())
