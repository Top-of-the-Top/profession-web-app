from unittest.mock import patch

from django.test import TestCase

from apps.webinars.models import Recording, Webinar
from apps.webinars.tests.test_models import (
    BaseWebinarTestCase,
    create_test_course,
    create_test_lesson,
    create_test_section,
)


class WebinarSignalsTest(BaseWebinarTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course(title="Signal Course")
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)

    @patch("apps.webinars.signals.invalidate_lesson_detail_cache")
    @patch("apps.webinars.signals.invalidate_schedule_cache")
    def test_webinar_save_invalidates_lesson_cache(self, mock_sched, mock_lesson):
        webinar = Webinar.objects.create(lesson=self.lesson)
        mock_lesson.assert_called_with(self.course.slug, self.lesson.slug)
        mock_sched.assert_called()

    @patch("apps.webinars.signals.invalidate_lesson_detail_cache")
    @patch("apps.webinars.signals.invalidate_schedule_cache")
    def test_webinar_delete_invalidates_lesson_cache(self, mock_sched, mock_lesson):
        webinar = Webinar.objects.create(lesson=self.lesson)
        mock_lesson.reset_mock()
        mock_sched.reset_mock()
        webinar.delete()
        mock_lesson.assert_called_with(self.course.slug, self.lesson.slug)
        mock_sched.assert_called()

    @patch("apps.webinars.signals.invalidate_lesson_detail_cache")
    @patch("apps.webinars.signals.invalidate_schedule_cache")
    def test_recording_save_invalidates_lesson_cache(self, mock_sched, mock_lesson):
        webinar = Webinar.objects.create(lesson=self.lesson)
        mock_lesson.reset_mock()
        mock_sched.reset_mock()
        Recording.objects.create(webinar=webinar)
        mock_lesson.assert_called_with(self.course.slug, self.lesson.slug)

    @patch("apps.webinars.signals.invalidate_lesson_detail_cache")
    @patch("apps.webinars.signals.invalidate_schedule_cache")
    def test_recording_delete_invalidates_lesson_cache(self, mock_sched, mock_lesson):
        webinar = Webinar.objects.create(lesson=self.lesson)
        rec = Recording.objects.create(webinar=webinar)
        mock_lesson.reset_mock()
        rec.delete()
        mock_lesson.assert_called_with(self.course.slug, self.lesson.slug)

    @patch("apps.webinars.signals.invalidate_lesson_detail_cache")
    @patch("apps.webinars.signals.invalidate_schedule_cache")
    def test_webinar_save_does_not_raise_on_repeated_saves(self, _mock_sched, _mock_lesson):
        webinar = Webinar.objects.create(lesson=self.lesson)
        webinar.status = Webinar.LIVE_STATUS
        webinar.save()
        webinar.refresh_from_db()
        self.assertEqual(webinar.status, Webinar.LIVE_STATUS)
