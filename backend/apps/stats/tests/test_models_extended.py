from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.test import TestCase
from django.utils import timezone

from apps.courses.tests.test_models import (
    create_test_course,
    create_test_lesson,
    create_test_section,
    create_test_user,
)
from apps.stats.models import LessonProgress, RecordingView, WebinarAttendance
from apps.webinars.models import Recording, Webinar


def make_webinar(lesson):
    return Webinar.objects.create(lesson=lesson)


def make_recording(webinar):
    return Recording.objects.create(webinar=webinar)


class WebinarAttendanceModelTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="watt_st@test.local", role="student")
        course = create_test_course(title="Attendance Course")
        section = create_test_section(course)
        self.lesson = create_test_lesson(section)
        self.webinar = make_webinar(self.lesson)

    def test_attendance_default_watched_seconds_zero(self):
        att = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=timezone.now()
        )
        self.assertEqual(att.watched_seconds, 0)

    def test_attendance_left_at_null_by_default(self):
        att = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=timezone.now()
        )
        self.assertIsNone(att.left_at)

    def test_attendance_multiple_per_user_and_webinar_allowed(self):
        att1 = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=timezone.now()
        )
        att2 = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=timezone.now()
        )
        self.assertEqual(WebinarAttendance.objects.filter(webinar=self.webinar).count(), 2)

    def test_attendance_cascade_deleted_with_user(self):
        att = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=timezone.now()
        )
        aid = att.attendance_id
        self.student.delete()
        self.assertFalse(WebinarAttendance.objects.filter(attendance_id=aid).exists())

    def test_attendance_cascade_deleted_with_webinar(self):
        att = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=timezone.now()
        )
        aid = att.attendance_id
        self.webinar.delete()
        self.assertFalse(WebinarAttendance.objects.filter(attendance_id=aid).exists())

    def test_attendance_ordering_newest_joined_first(self):
        from datetime import timedelta

        earlier = timezone.now() - timedelta(hours=2)
        later = timezone.now()
        att1 = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=earlier
        )
        att2 = WebinarAttendance.objects.create(
            user=self.student, webinar=self.webinar, joined_at=later
        )
        atts = list(WebinarAttendance.objects.all())
        self.assertEqual(atts[0], att2)


class RecordingViewModelTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="rv_st@test.local", role="student")
        course = create_test_course(title="RecView Course")
        section = create_test_section(course)
        self.lesson = create_test_lesson(section)
        self.webinar = make_webinar(self.lesson)
        self.recording = make_recording(self.webinar)

    def test_recording_view_default_watched_zero(self):
        rv = RecordingView.objects.create(user=self.student, recording=self.recording)
        self.assertEqual(rv.watched_seconds, 0)
        self.assertEqual(rv.last_position, 0)

    def test_recording_view_unique_per_user_and_recording(self):
        RecordingView.objects.create(user=self.student, recording=self.recording)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                RecordingView.objects.create(user=self.student, recording=self.recording)

    def test_recording_view_update_watched_seconds(self):
        rv = RecordingView.objects.create(
            user=self.student, recording=self.recording, watched_seconds=120
        )
        rv.watched_seconds = 300
        rv.save()
        rv.refresh_from_db()
        self.assertEqual(rv.watched_seconds, 300)

    def test_recording_view_cascade_deleted_with_user(self):
        rv = RecordingView.objects.create(user=self.student, recording=self.recording)
        vid = rv.view_id
        self.student.delete()
        self.assertFalse(RecordingView.objects.filter(view_id=vid).exists())

    def test_recording_view_cascade_deleted_with_recording(self):
        rv = RecordingView.objects.create(user=self.student, recording=self.recording)
        vid = rv.view_id
        self.recording.delete()
        self.assertFalse(RecordingView.objects.filter(view_id=vid).exists())


class LessonProgressModelTests(TestCase):

    def setUp(self):
        self.student = create_test_user(email="lp_st@test.local", role="student")
        course = create_test_course(title="Progress Course")
        section = create_test_section(course)
        self.lesson = create_test_lesson(section)

    def test_lesson_progress_defaults(self):
        lp = LessonProgress.objects.create(user=self.student, lesson=self.lesson)
        self.assertEqual(lp.watched_ratio, 0.0)
        self.assertFalse(lp.all_homeworks_submitted)
        self.assertFalse(lp.is_completed)
        self.assertIsNone(lp.completed_at)

    def test_lesson_progress_unique_per_user_and_lesson(self):
        LessonProgress.objects.create(user=self.student, lesson=self.lesson)
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                LessonProgress.objects.create(user=self.student, lesson=self.lesson)

    def test_lesson_progress_complete(self):
        lp = LessonProgress.objects.create(user=self.student, lesson=self.lesson)
        lp.is_completed = True
        lp.completed_at = timezone.now()
        lp.watched_ratio = 1.0
        lp.all_homeworks_submitted = True
        lp.save()
        lp.refresh_from_db()
        self.assertTrue(lp.is_completed)
        self.assertIsNotNone(lp.completed_at)
        self.assertEqual(lp.watched_ratio, 1.0)

    def test_lesson_progress_cascade_deleted_with_user(self):
        lp = LessonProgress.objects.create(user=self.student, lesson=self.lesson)
        pid = lp.progress_id
        self.student.delete()
        self.assertFalse(LessonProgress.objects.filter(progress_id=pid).exists())

    def test_lesson_progress_cascade_deleted_with_lesson(self):
        lp = LessonProgress.objects.create(user=self.student, lesson=self.lesson)
        pid = lp.progress_id
        self.lesson.delete()
        self.assertFalse(LessonProgress.objects.filter(progress_id=pid).exists())
