from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.courses.models import Course, Homework, Lesson, Section
from apps.homeworks.models import Attempt
from apps.stats.models import LessonProgress, RecordingView, WebinarAttendance
from apps.stats.services.progress_service import recompute_lesson_progress
from apps.users.models import User
from apps.webinars.models import Recording, Webinar


class RecomputeLessonProgressTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email_cipher="x", password="p")
        author = User.objects.create_user(
            email_cipher="a", password="p", role=User.ROLE_TEACHER
        )
        self.course = Course.objects.create(
            title="C", sub_title="s", description="d", price=0
        )
        self.course.authors.add(author)
        self.section = Section.objects.create(course=self.course, title="S")
        self.lesson = Lesson.objects.create(section=self.section, title="L")

    def test_lesson_without_webinar_and_homeworks_is_completed(self):
        progress = recompute_lesson_progress(user=self.user, lesson=self.lesson)
        self.assertTrue(progress.is_completed)

    def test_completed_when_watched_70_and_all_hw_submitted(self):
        webinar = Webinar.objects.create(
            lesson=self.lesson,
            started_at=timezone.now() - timedelta(hours=1),
            ended_at=timezone.now(),
        )
        hw = Homework.objects.create(
            lesson=self.lesson, title="hw", deadline=timezone.now() + timedelta(days=1)
        )
        WebinarAttendance.objects.create(
            user=self.user,
            webinar=webinar,
            joined_at=timezone.now() - timedelta(hours=1),
            left_at=timezone.now(),
            watched_seconds=int(3600 * 0.8),
        )
        Attempt.objects.create(
            user=self.user, homework=hw, status=Attempt.SUBMITTED_STATUS,
            send_at=timezone.now(),
        )
        progress = recompute_lesson_progress(user=self.user, lesson=self.lesson)
        self.assertTrue(progress.is_completed)
        self.assertTrue(progress.all_homeworks_submitted)
        self.assertGreaterEqual(progress.watched_ratio, 0.7)
        self.assertIsNotNone(progress.completed_at)

    def test_recording_ratio_uses_recording_duration_not_webinar(self):
        webinar = Webinar.objects.create(
            lesson=self.lesson,
            started_at=timezone.now() - timedelta(hours=1),
            ended_at=timezone.now(),
        )
        recording = Recording.objects.create(
            webinar=webinar, duration_seconds=1800
        )
        RecordingView.objects.create(
            user=self.user,
            recording=recording,
            watched_seconds=int(1800 * 0.8),
            last_position=int(1800 * 0.8),
        )
        progress = recompute_lesson_progress(user=self.user, lesson=self.lesson)
        self.assertAlmostEqual(progress.watched_ratio, 0.8, places=2)

    def test_partial_homework_submission_not_enough(self):
        Homework.objects.create(
            lesson=self.lesson, title="hw1", deadline=timezone.now() + timedelta(days=1)
        )
        hw2 = Homework.objects.create(
            lesson=self.lesson, title="hw2", deadline=timezone.now() + timedelta(days=1)
        )
        Attempt.objects.create(
            user=self.user, homework=hw2, status=Attempt.SUBMITTED_STATUS,
            send_at=timezone.now(),
        )
        progress = recompute_lesson_progress(user=self.user, lesson=self.lesson)
        self.assertFalse(progress.all_homeworks_submitted)
        self.assertFalse(progress.is_completed)
