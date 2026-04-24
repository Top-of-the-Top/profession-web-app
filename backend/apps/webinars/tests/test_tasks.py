import time
from unittest.mock import patch, MagicMock

from django.utils import timezone

from ..models import Webinar, Recording
from ..tasks import (
    check_idle_webinars,
    upload_recording_to_kinescope,
    check_kinescope_processing,
)
from .test_models import (
    BaseWebinarTestCase,
    create_test_course,
    create_test_section,
    create_test_lesson,
)


class CheckIdleWebinarsTest(BaseWebinarTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.webinar = Webinar.objects.create(
            lesson=self.lesson,
            status=Webinar.LIVE_STATUS,
            whiteboard_room_uuid='room-x',
        )

        from django.core.cache import caches
        caches['default'].clear()

    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_does_not_touch_webinar_with_active_users(self, mock_count, mock_ban):
        mock_count.return_value = 3
        check_idle_webinars()

        self.webinar.refresh_from_db()
        self.assertEqual(self.webinar.status, Webinar.LIVE_STATUS)
        mock_ban.assert_not_called()

    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_starts_idle_countdown_on_first_empty_poll(self, mock_count, mock_ban):
        mock_count.return_value = 0
        check_idle_webinars()

        from django.core.cache import caches
        key = f'webinar_empty_since:{self.webinar.webinar_id}'
        self.assertIsNotNone(caches['default'].get(key))

        self.webinar.refresh_from_db()
        self.assertEqual(self.webinar.status, Webinar.LIVE_STATUS)
        mock_ban.assert_not_called()

    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_keeps_webinar_live_before_threshold_elapses(self, mock_count, mock_ban):
        mock_count.return_value = 0

        from django.core.cache import caches
        caches['default'].set(
            f'webinar_empty_since:{self.webinar.webinar_id}',
            time.time() - 60,
            timeout=300,
        )

        check_idle_webinars()

        self.webinar.refresh_from_db()
        self.assertEqual(self.webinar.status, Webinar.LIVE_STATUS)
        mock_ban.assert_not_called()

    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_stops_webinar_after_idle_threshold(self, mock_count, mock_ban):
        mock_count.return_value = 0

        from django.core.cache import caches
        caches['default'].set(
            f'webinar_empty_since:{self.webinar.webinar_id}',
            time.time() - 400,
            timeout=600,
        )

        check_idle_webinars()

        self.webinar.refresh_from_db()
        self.assertEqual(self.webinar.status, Webinar.ENDED_STATUS)
        self.assertIsNotNone(self.webinar.ended_at)
        mock_ban.assert_called_once_with('room-x')

    @patch('apps.webinars.api.views._stop_recording')
    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_stops_active_recording_on_idle_stop(self, mock_count, mock_ban, mock_stop_rec):
        mock_count.return_value = 0
        Recording.objects.create(webinar=self.webinar, status=Recording.RECORDING_STATUS)

        from django.core.cache import caches
        caches['default'].set(
            f'webinar_empty_since:{self.webinar.webinar_id}',
            time.time() - 400,
            timeout=600,
        )

        check_idle_webinars()
        mock_stop_rec.assert_called_once()

    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_agora_failure_skips_webinar(self, mock_count):
        mock_count.side_effect = Exception('agora down')

        check_idle_webinars()

        self.webinar.refresh_from_db()
        self.assertEqual(self.webinar.status, Webinar.LIVE_STATUS)

    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_clears_cache_when_users_return(self, mock_count, mock_ban):
        from django.core.cache import caches
        key = f'webinar_empty_since:{self.webinar.webinar_id}'
        caches['default'].set(key, time.time() - 60, timeout=600)

        mock_count.return_value = 5
        check_idle_webinars()

        self.assertIsNone(caches['default'].get(key))

    @patch('apps.webinars.api.utils.agora_utils.ban_whiteboard_room')
    @patch('apps.webinars.api.utils.agora_utils.get_channel_user_count')
    def test_ignores_webinars_not_live(self, mock_count, mock_ban):
        self.webinar.status = Webinar.ENDED_STATUS
        self.webinar.save()

        check_idle_webinars()
        mock_count.assert_not_called()


class UploadRecordingTaskTest(BaseWebinarTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.webinar = Webinar.objects.create(lesson=self.lesson)

    def test_returns_error_for_missing_recording(self):
        result = upload_recording_to_kinescope('00000000-0000-0000-0000-000000000000')
        self.assertEqual(result['status'], 'error')

    def test_skipped_when_no_recording_url(self):
        rec = Recording.objects.create(webinar=self.webinar)
        result = upload_recording_to_kinescope(str(rec.recording_id))
        self.assertEqual(result['status'], 'skipped')

    def test_skipped_when_already_uploaded(self):
        rec = Recording.objects.create(
            webinar=self.webinar,
            recording_url='recordings/file.mp4',
            kinescope_video_id='already-there',
        )
        result = upload_recording_to_kinescope(str(rec.recording_id))
        self.assertEqual(result['status'], 'skipped')

    @patch('apps.webinars.tasks.check_kinescope_processing')
    @patch('apps.webinars.api.utils.kinescope_utils.upload_video_by_url')
    @patch('apps.webinars.api.utils.kinescope_utils.create_folder')
    def test_uploads_and_schedules_status_check(self, mock_folder, mock_upload, mock_check):
        mock_folder.return_value = 'folder-xyz'
        mock_upload.return_value = {'id': 'vid-new'}
        mock_check.apply_async = MagicMock()

        rec = Recording.objects.create(
            webinar=self.webinar,
            recording_url='recordings/file.mp4',
            started_at=timezone.now(),
        )

        result = upload_recording_to_kinescope(str(rec.recording_id))

        self.assertEqual(result['status'], 'uploaded')
        self.assertEqual(result['video_id'], 'vid-new')

        rec.refresh_from_db()
        self.assertEqual(rec.kinescope_video_id, 'vid-new')
        self.assertEqual(rec.kinescope_upload_status, 'processing')

        self.course.refresh_from_db()
        self.assertEqual(self.course.kinescope_folder_id, 'folder-xyz')

        mock_check.apply_async.assert_called_once()

    @patch('apps.webinars.api.utils.kinescope_utils.upload_video_by_url')
    @patch('apps.webinars.api.utils.kinescope_utils.create_folder')
    def test_reuses_existing_folder(self, mock_folder, mock_upload):
        self.course.kinescope_folder_id = 'existing-folder'
        self.course.save()

        mock_upload.return_value = {'id': 'vid'}

        rec = Recording.objects.create(
            webinar=self.webinar,
            recording_url='recordings/file.mp4',
            started_at=timezone.now(),
        )
        with patch('apps.webinars.tasks.check_kinescope_processing.apply_async'):
            upload_recording_to_kinescope(str(rec.recording_id))

        mock_folder.assert_not_called()

    @patch('apps.webinars.api.utils.kinescope_utils.upload_video_by_url')
    def test_builds_full_s3_url_for_relative_path(self, mock_upload):
        mock_upload.return_value = {'id': 'v'}
        self.course.kinescope_folder_id = 'f'
        self.course.save()

        rec = Recording.objects.create(
            webinar=self.webinar,
            recording_url='recordings/file.mp4',
            started_at=timezone.now(),
        )
        with patch('apps.webinars.tasks.check_kinescope_processing.apply_async'):
            with patch.dict('os.environ', {'AWS_S3_BUCKET_NAME': 'my-bucket'}):
                upload_recording_to_kinescope(str(rec.recording_id))

        _, kwargs = mock_upload.call_args
        self.assertTrue(kwargs['video_url'].startswith('https://storage.yandexcloud.net/my-bucket/'))

    @patch('apps.webinars.api.utils.kinescope_utils.upload_video_by_url')
    def test_passes_absolute_url_as_is(self, mock_upload):
        mock_upload.return_value = {'id': 'v'}
        self.course.kinescope_folder_id = 'f'
        self.course.save()

        rec = Recording.objects.create(
            webinar=self.webinar,
            recording_url='https://example.com/video.mp4',
            started_at=timezone.now(),
        )
        with patch('apps.webinars.tasks.check_kinescope_processing.apply_async'):
            upload_recording_to_kinescope(str(rec.recording_id))

        _, kwargs = mock_upload.call_args
        self.assertEqual(kwargs['video_url'], 'https://example.com/video.mp4')

    @patch('apps.webinars.api.utils.kinescope_utils.upload_video_by_url')
    def test_marks_failed_and_raises_on_upload_error(self, mock_upload):
        mock_upload.side_effect = Exception('boom')
        self.course.kinescope_folder_id = 'f'
        self.course.save()

        rec = Recording.objects.create(
            webinar=self.webinar,
            recording_url='recordings/file.mp4',
            started_at=timezone.now(),
        )

        from celery.exceptions import Retry
        with self.assertRaises((Exception, Retry)):
            upload_recording_to_kinescope(str(rec.recording_id))

        rec.refresh_from_db()
        self.assertEqual(rec.kinescope_upload_status, 'failed')


class CheckKinescopeProcessingTest(BaseWebinarTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.webinar = Webinar.objects.create(lesson=self.lesson)

    def test_returns_error_for_missing_recording(self):
        result = check_kinescope_processing('00000000-0000-0000-0000-000000000000')
        self.assertEqual(result['status'], 'error')

    def test_returns_error_when_no_video_id(self):
        rec = Recording.objects.create(webinar=self.webinar)
        result = check_kinescope_processing(str(rec.recording_id))
        self.assertEqual(result['status'], 'error')

    @patch('apps.webinars.api.utils.kinescope_utils.get_video_status')
    def test_marks_ready_on_ready_status(self, mock_status):
        mock_status.return_value = {'status': 'ready'}
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_video_id='vid',
            kinescope_upload_status='processing',
        )

        result = check_kinescope_processing(str(rec.recording_id))

        self.assertEqual(result['status'], 'ready')
        rec.refresh_from_db()
        self.assertEqual(rec.kinescope_upload_status, 'ready')

    @patch('apps.webinars.api.utils.kinescope_utils.get_video_status')
    def test_marks_failed_on_error_status(self, mock_status):
        mock_status.return_value = {'status': 'error'}
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_video_id='vid',
            kinescope_upload_status='processing',
        )

        result = check_kinescope_processing(str(rec.recording_id))

        self.assertEqual(result['status'], 'failed')
        rec.refresh_from_db()
        self.assertEqual(rec.kinescope_upload_status, 'failed')

    @patch('apps.webinars.api.utils.kinescope_utils.get_video_status')
    def test_marks_failed_on_failed_status(self, mock_status):
        mock_status.return_value = {'status': 'failed'}
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_video_id='vid',
        )
        result = check_kinescope_processing(str(rec.recording_id))
        self.assertEqual(result['status'], 'failed')

    @patch('apps.webinars.api.utils.kinescope_utils.get_video_status')
    def test_retries_on_pending_status(self, mock_status):
        mock_status.return_value = {'status': 'processing'}
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_video_id='vid',
        )

        from celery.exceptions import Retry
        with self.assertRaises((Retry, Exception)):
            check_kinescope_processing(str(rec.recording_id))
