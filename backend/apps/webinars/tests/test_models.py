from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.courses.models import Course, Lesson, Section
from apps.users.api.utils.crypto_utils import encrypt_data
from apps.users.models import User

from ..models import Recording, Webinar


def create_test_user(email="test@test.com", role="teacher"):
    return User.objects.create_user(
        email_cipher=encrypt_data(email),
        password="testpass123",
        role=role,
    )


def create_test_course(**kwargs):
    defaults = {
        "title": "Тестовый курс",
        "sub_title": "Краткое описание",
        "description": "Описание",
        "price": 9000,
    }
    defaults.update(kwargs)
    return Course.objects.create(**defaults)


def create_test_section(course, **kwargs):
    defaults = {
        "course": course,
        "title": "Тестовая секция",
    }
    defaults.update(kwargs)
    return Section.objects.create(**defaults)


def create_test_lesson(section, **kwargs):
    defaults = {
        "section": section,
        "title": "Тестовый урок",
    }
    defaults.update(kwargs)
    return Lesson.objects.create(**defaults)


class BaseWebinarTestCase(TestCase):
    """Мокаем celery-задачи, которые могут вызываться из сигналов courses."""

    CELERY_TASKS_TO_MOCK = [
        "apps.courses.signals.send_course_notification.delay",
        "apps.courses.signals.send_course_notification.apply_async",
        "apps.courses.signals.send_personal_notification.delay",
        "apps.courses.signals.send_mass_course_email.delay",
        "apps.courses.signals.send_mass_course_email.apply_async",
        "apps.courses.signals.send_mass_system_email.delay",
        "apps.courses.signals.send_single_email.delay",
    ]

    def setUp(self):
        super().setUp()
        self.celery_patchers = []
        for path in self.CELERY_TASKS_TO_MOCK:
            patcher = patch(path)
            patcher.start()
            self.celery_patchers.append(patcher)

    def tearDown(self):
        for p in self.celery_patchers:
            p.stop()
        super().tearDown()


class WebinarModelTest(BaseWebinarTestCase):
    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.user = create_test_user(email="teacher_m@test.com", role="teacher")

    def test_webinar_created_with_pending_status_by_default(self):
        webinar = Webinar.objects.create(lesson=self.lesson)
        self.assertEqual(webinar.status, Webinar.PENDING_STATUS)

    def test_webinar_generates_agora_channel_name_on_save(self):
        webinar = Webinar.objects.create(lesson=self.lesson)

        self.assertTrue(webinar.agora_channel_name.startswith("webinar-"))
        self.assertEqual(len(webinar.agora_channel_name), len("webinar-") + 8)

    def test_webinar_does_not_overwrite_existing_agora_channel_name(self):
        webinar = Webinar.objects.create(
            lesson=self.lesson,
            agora_channel_name="custom-channel",
        )
        original = webinar.agora_channel_name

        webinar.status = Webinar.LIVE_STATUS
        webinar.save()
        webinar.refresh_from_db()

        self.assertEqual(webinar.agora_channel_name, original)

    def test_webinar_agora_channel_name_is_unique(self):
        Webinar.objects.create(
            lesson=self.lesson,
            agora_channel_name="unique-channel",
        )

        other_lesson = create_test_lesson(self.section, title="Другой урок")
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Webinar.objects.create(
                    lesson=other_lesson,
                    agora_channel_name="unique-channel",
                )

    def test_webinar_has_one_to_one_with_lesson(self):
        Webinar.objects.create(lesson=self.lesson)

        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Webinar.objects.create(lesson=self.lesson)

    def test_webinar_cascade_deleted_when_lesson_deleted(self):
        webinar = Webinar.objects.create(lesson=self.lesson)
        webinar_id = webinar.webinar_id

        self.lesson.delete()

        self.assertFalse(Webinar.objects.filter(webinar_id=webinar_id).exists())

    def test_webinar_started_by_set_null_on_user_delete(self):
        webinar = Webinar.objects.create(lesson=self.lesson, started_by=self.user)
        self.user.delete()
        webinar.refresh_from_db()

        self.assertIsNone(webinar.started_by)

    def test_webinar_str_contains_lesson_title(self):
        self.lesson.title = "Мой урок"
        self.lesson.save()
        webinar = Webinar.objects.create(lesson=self.lesson)

        self.assertIn("Мой урок", str(webinar))

    def test_webinar_status_choices(self):
        statuses = [s[0] for s in Webinar.STATUS_CHOICES]
        self.assertIn(Webinar.PENDING_STATUS, statuses)
        self.assertIn(Webinar.LIVE_STATUS, statuses)
        self.assertIn(Webinar.ENDED_STATUS, statuses)


class RecordingModelTest(BaseWebinarTestCase):
    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.webinar = Webinar.objects.create(lesson=self.lesson)
        self.user = create_test_user(email="recstart@test.com", role="teacher")

    def test_recording_default_status_is_recording(self):
        rec = Recording.objects.create(webinar=self.webinar)
        self.assertEqual(rec.status, Recording.RECORDING_STATUS)

    def test_recording_default_kinescope_upload_status_is_none(self):
        rec = Recording.objects.create(webinar=self.webinar)
        self.assertEqual(rec.kinescope_upload_status, "none")

    def test_recording_cascade_deleted_when_webinar_deleted(self):
        rec = Recording.objects.create(webinar=self.webinar)
        rec_id = rec.recording_id

        self.webinar.delete()
        self.assertFalse(Recording.objects.filter(recording_id=rec_id).exists())

    def test_recording_started_by_set_null_on_user_delete(self):
        rec = Recording.objects.create(webinar=self.webinar, started_by=self.user)
        self.user.delete()
        rec.refresh_from_db()
        self.assertIsNone(rec.started_by)

    def test_recording_soft_delete_default(self):
        rec = Recording.objects.create(webinar=self.webinar)
        self.assertFalse(rec.is_deleted)
        self.assertIsNone(rec.deleted_at)
        self.assertIsNone(rec.deleted_by)

    def test_recording_deleted_by_set_null_on_user_delete(self):
        rec = Recording.objects.create(
            webinar=self.webinar,
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=self.user,
        )
        self.user.delete()
        rec.refresh_from_db()
        self.assertIsNone(rec.deleted_by)
        self.assertTrue(rec.is_deleted)

    def test_multiple_recordings_per_webinar_allowed(self):
        Recording.objects.create(webinar=self.webinar)
        Recording.objects.create(webinar=self.webinar)

        self.assertEqual(self.webinar.recordings.count(), 2)

    def test_recording_ordering_by_started_at_desc(self):
        older = Recording.objects.create(
            webinar=self.webinar,
            started_at=timezone.now() - timedelta(hours=2),
        )
        newer = Recording.objects.create(
            webinar=self.webinar,
            started_at=timezone.now(),
        )

        recs = list(Recording.objects.all())
        self.assertEqual(recs[0], newer)
        self.assertEqual(recs[1], older)

    def test_recording_status_choices(self):
        statuses = [s[0] for s in Recording.STATUS_CHOICES]
        self.assertIn(Recording.RECORDING_STATUS, statuses)
        self.assertIn(Recording.PROCESSING_STATUS, statuses)
        self.assertIn(Recording.READY_STATUS, statuses)
        self.assertIn(Recording.FAILED_STATUS, statuses)

    def test_recording_kinescope_upload_status_choices(self):
        statuses = [s[0] for s in Recording.KINESCOPE_UPLOAD_STATUS_CHOICES]
        for expected in (
            "none",
            "pending",
            "uploading",
            "processing",
            "ready",
            "failed",
        ):
            self.assertIn(expected, statuses)
