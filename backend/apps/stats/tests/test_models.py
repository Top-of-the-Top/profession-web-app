from django.test import TestCase
from django.utils import timezone

from apps.courses.models import Course, Lesson, Section
from apps.stats.models import LessonProgress, RecordingView, WebinarAttendance
from apps.users.models import User
from apps.webinars.models import Recording, Webinar


class StatisticsModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email_cipher="enc_email", password="pass12345")
        author = User.objects.create_user(email_cipher="enc_author", password="pass12345")
        self.course = Course.objects.create(title="Тест", sub_title="t", description="d", price=0)
        self.course.authors.add(author)
        self.section = Section.objects.create(course=self.course, title="С1")
        self.lesson = Lesson.objects.create(section=self.section, title="У1")
        self.webinar = Webinar.objects.create(lesson=self.lesson)
        self.recording = Recording.objects.create(webinar=self.webinar)

    def test_webinar_attendance_create(self):
        att = WebinarAttendance.objects.create(
            user=self.user,
            webinar=self.webinar,
            joined_at=timezone.now(),
            watched_seconds=120,
        )
        self.assertEqual(att.watched_seconds, 120)
        self.assertIsNone(att.left_at)

    def test_recording_view_unique(self):
        RecordingView.objects.create(user=self.user, recording=self.recording, watched_seconds=10)
        with self.assertRaises(Exception):
            RecordingView.objects.create(
                user=self.user, recording=self.recording, watched_seconds=20
            )

    def test_lesson_progress_default_not_completed(self):
        lp = LessonProgress.objects.create(user=self.user, lesson=self.lesson)
        self.assertFalse(lp.is_completed)
        self.assertEqual(lp.watched_ratio, 0.0)
