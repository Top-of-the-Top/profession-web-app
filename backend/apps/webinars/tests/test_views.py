import base64
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.courses.models import CourseEnrollment
from apps.payments.models import Payment
from apps.users.api.utils.token_utils import get_tokens_for_user

from ..api.utils.agora_utils import make_recorder_token
from ..models import Recording, Webinar
from .test_models import (
    BaseWebinarTestCase,
    create_test_course,
    create_test_lesson,
    create_test_section,
    create_test_user,
)


class ViewTestMixin:

    def authenticate(self, user):
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def enroll(self, user, course):
        from datetime import timedelta

        payment = Payment.objects.create(user=user, total_sum=1000, status="success")
        CourseEnrollment.objects.create(
            user=user,
            course=course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )


class WebinarEndpointsBase(BaseWebinarTestCase, ViewTestMixin):

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.teacher = create_test_user(email="teacher_wv@test.com", role="teacher")
        self.other_teacher = create_test_user(email="other_teacher_wv@test.com", role="teacher")
        self.student = create_test_user(email="student_wv@test.com", role="student")
        self.moderator = create_test_user(email="mod_wv@test.com", role="moderator")
        self.course = create_test_course()
        self.course.authors.add(self.teacher)
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.enroll(self.student, self.course)

    def url_start(self):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/start/"

    def url_schedule(self):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/schedule/"

    def url_stop(self):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/stop/"

    def url_join(self):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/join/"

    def url_recorder_join(self):
        return (
            f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/recorder-join/"
        )

    def url_rec_start(self):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/recording/start/"

    def url_rec_stop(self):
        return (
            f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/webinar/recording/stop/"
        )

    def url_pdf(self, rec_id):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/recordings/{rec_id}/pdf/"

    def url_rec_delete(self, rec_id):
        return f"/api/v1/courses/{self.course.slug}/lessons/{self.lesson.slug}/recordings/{rec_id}/"


@patch("apps.webinars.api.views.create_whiteboard_room", return_value="room-new")
@patch("apps.webinars.api.views.ban_whiteboard_room")
class WebinarStartViewTest(WebinarEndpointsBase):

    def test_requires_authentication(self, *_):
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_start(self, *_):
        self.authenticate(self.student)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_teacher_cannot_start(self, *_):
        self.authenticate(self.other_teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_start_webinar(self, *_):
        self.authenticate(self.teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("webinar_id", response.data)
        webinar = Webinar.objects.get(lesson=self.lesson)
        self.assertEqual(webinar.status, Webinar.LIVE_STATUS)
        self.assertEqual(webinar.started_by, self.teacher)
        self.assertIsNotNone(webinar.started_at)
        self.assertEqual(webinar.whiteboard_room_uuid, "room-new")

    def test_moderator_can_start(self, *_):
        self.authenticate(self.moderator)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_start_on_live_webinar_returns_existing_without_recreating_room(
        self, mock_ban, mock_create, *args
    ):
        existing = Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="live-room"
        )
        self.authenticate(self.teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["webinar_id"], str(existing.webinar_id))
        existing.refresh_from_db()
        self.assertEqual(existing.whiteboard_room_uuid, "live-room")
        mock_create.assert_not_called()
        mock_ban.assert_not_called()

    def test_whiteboard_creation_failure_returns_502(self, mock_ban, mock_create, *args):
        mock_create.side_effect = Exception("netless down")
        self.authenticate(self.teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(
            Webinar.objects.filter(lesson=self.lesson, status=Webinar.LIVE_STATUS).exists()
        )

    def test_old_whiteboard_banned_on_restart(self, mock_ban, mock_create, *args):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.ENDED_STATUS, whiteboard_room_uuid="old-room"
        )
        self.authenticate(self.teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_ban.assert_called_once_with("old-room")

    def test_ban_old_room_exception_does_not_fail_start(self, mock_ban, mock_create, *args):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.ENDED_STATUS, whiteboard_room_uuid="old-room"
        )
        mock_ban.side_effect = Exception("netless error")
        self.authenticate(self.teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_404_for_nonexistent_lesson(self, *_):
        self.authenticate(self.teacher)
        url = f"/api/v1/courses/{self.course.slug}/lessons/no-such-lesson/webinar/start/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_for_mismatched_course_and_lesson(self, *_):
        other_course = create_test_course(title="Другой курс")
        other_section = create_test_section(other_course)
        other_lesson = create_test_lesson(other_section, title="урок")
        self.authenticate(self.teacher)
        url = f"/api/v1/courses/{self.course.slug}/lessons/{other_lesson.slug}/webinar/start/"
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@patch("apps.webinars.api.views.ban_whiteboard_room")
class WebinarStopViewTest(WebinarEndpointsBase):

    def test_requires_authentication(self, *_):
        response = self.client.post(self.url_stop())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_stop(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.student)
        response = self.client.post(self.url_stop())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stops_live_webinar(self, *_):
        webinar = Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-x"
        )
        self.authenticate(self.teacher)
        response = self.client.post(self.url_stop())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        webinar.refresh_from_db()
        self.assertEqual(webinar.status, Webinar.ENDED_STATUS)
        self.assertIsNotNone(webinar.ended_at)

    def test_returns_404_if_webinar_does_not_exist(self, *_):
        self.authenticate(self.teacher)
        response = self.client.post(self.url_stop())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.webinars.api.views._stop_recording")
    def test_stops_active_recording_if_any(self, mock_stop_rec, *_):
        webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        rec = Recording.objects.create(webinar=webinar, status=Recording.RECORDING_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_stop())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_stop_rec.assert_called_once()
        self.assertEqual(mock_stop_rec.call_args[0][0].pk, rec.pk)

    def test_ban_whiteboard_exception_does_not_fail_stop(self, mock_ban, *_):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-x"
        )
        mock_ban.side_effect = Exception("err")
        self.authenticate(self.teacher)
        response = self.client.post(self.url_stop())
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@patch("apps.webinars.api.views.generate_rtm_token", return_value="rtm-tok")
@patch("apps.webinars.api.views.generate_whiteboard_room_token", return_value="wb-tok")
@patch("apps.webinars.api.views.generate_rtc_token", return_value="rtc-tok")
class WebinarJoinViewTest(WebinarEndpointsBase):

    def test_requires_authentication(self, *_):
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_404_when_no_live_webinar(self, *_):
        self.authenticate(self.student)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_404_when_webinar_is_pending(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.PENDING_STATUS)
        self.authenticate(self.student)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_not_enrolled_forbidden(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        other_student = create_test_user(email="outsider@test.com", role="student")
        self.authenticate(other_student)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enrolled_student_gets_writer_role(self, *_):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-1"
        )
        self.authenticate(self.student)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "student")
        self.assertEqual(response.data["rtc_token"], "rtc-tok")
        self.assertEqual(response.data["rtm_token"], "rtm-tok")
        self.assertEqual(response.data["chat_channel_name"], "chat-room-1")
        self.assertEqual(response.data["whiteboard_room_token"], "wb-tok")
        self.assertEqual(response.data["whiteboard_room_uuid"], "room-1")

    def test_chat_channel_name_uses_whiteboard_room_uuid(self, *_):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="abc-xyz-123"
        )
        self.authenticate(self.teacher)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["chat_channel_name"], "chat-abc-xyz-123")

    def test_rtm_token_called_with_uid(self, mock_rtc, mock_wb, mock_rtm):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-x"
        )
        self.authenticate(self.teacher)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_rtm.assert_called_once_with(response.data["uid"])

    def test_author_gets_teacher_role(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.teacher)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "teacher")

    def test_moderator_gets_teacher_role(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.moderator)
        response = self.client.get(self.url_join())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "teacher")

    def test_whiteboard_role_mapping(self, mock_rtc, mock_wb, mock_rtm):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-1"
        )
        self.authenticate(self.teacher)
        self.client.get(self.url_join())
        _, kwargs = mock_wb.call_args
        self.assertEqual(kwargs.get("role"), "admin")
        mock_wb.reset_mock()
        self.authenticate(self.student)
        self.client.get(self.url_join())
        _, kwargs = mock_wb.call_args
        self.assertEqual(kwargs.get("role"), "writer")


@patch("apps.webinars.api.views.generate_rtm_token", return_value="rtm-tok")
@patch("apps.webinars.api.views.generate_whiteboard_room_token", return_value="wb-tok")
@patch("apps.webinars.api.views.generate_rtc_token", return_value="rtc-tok")
class WebinarRecorderJoinViewTest(WebinarEndpointsBase):

    def test_missing_token_returns_400(self, *_):
        response = self.client.get(self.url_recorder_join())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_token_returns_403(self, *_):
        response = self.client.get(self.url_recorder_join() + "?token=bad-token")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_token_but_no_live_webinar_returns_404(self, *_):
        webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.PENDING_STATUS)
        token = make_recorder_token(str(webinar.webinar_id))
        response = self.client.get(self.url_recorder_join() + f"?token={token}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_token_returns_recorder_tokens(self, *_):
        webinar = Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-r"
        )
        token = make_recorder_token(str(webinar.webinar_id))
        response = self.client.get(self.url_recorder_join() + f"?token={token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "recorder")
        self.assertEqual(response.data["uid"], 999999)
        self.assertEqual(response.data["rtc_token"], "rtc-tok")
        self.assertEqual(response.data["rtm_token"], "rtm-tok")
        self.assertEqual(response.data["chat_channel_name"], "chat-room-r")
        self.assertEqual(response.data["whiteboard_room_token"], "wb-tok")


@patch("apps.webinars.api.views.recording_start_web", return_value="sid-1")
@patch("apps.webinars.api.views.recording_acquire", return_value="res-1")
class WebinarRecordingStartViewTest(WebinarEndpointsBase):

    def test_requires_authentication(self, *_):
        response = self.client.post(self.url_rec_start())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_start_recording(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.student)
        response = self.client.post(self.url_rec_start())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_404_without_live_webinar(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.PENDING_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_rec_start())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_start_when_recording_already_in_progress(self, *_):
        webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        Recording.objects.create(webinar=webinar, status=Recording.RECORDING_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_rec_start())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_starts_recording_and_stores_sid_and_resource(self, mock_acq, mock_start, *_):
        webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_rec_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recording_id", response.data)
        rec = Recording.objects.get(webinar=webinar)
        self.assertEqual(rec.status, Recording.RECORDING_STATUS)
        self.assertEqual(rec.resource_id, "res-1")
        self.assertEqual(rec.sid, "sid-1")
        self.assertEqual(rec.started_by, self.teacher)
        self.assertIsNotNone(rec.started_at)
        mock_acq.assert_called_once()
        mock_start.assert_called_once()


class WebinarRecordingStopViewTest(WebinarEndpointsBase):

    def test_student_cannot_stop_recording(self):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.student)
        response = self.client.post(self.url_rec_stop())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_404_without_live_webinar(self):
        self.authenticate(self.teacher)
        response = self.client.post(self.url_rec_stop())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_400_when_no_active_recording(self):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_rec_stop())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.webinars.api.views._stop_recording")
    def test_stops_active_recording(self, mock_stop):
        webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        rec = Recording.objects.create(webinar=webinar, status=Recording.RECORDING_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_rec_stop())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["recording_id"]), str(rec.recording_id))
        mock_stop.assert_called_once()


class StopRecordingHelperTest(WebinarEndpointsBase):

    def setUp(self):
        super().setUp()
        self.webinar = Webinar.objects.create(
            lesson=self.lesson, status=Webinar.LIVE_STATUS, whiteboard_room_uuid="room-x"
        )

    @patch("apps.webinars.tasks.upload_recording_to_kinescope.delay")
    @patch("apps.webinars.api.views.recording_stop_web")
    def test_stop_recording_queues_upload_when_url_present(self, mock_stop, mock_upload):
        mock_stop.return_value = {
            "serverResponse": {
                "extensionServiceState": [
                    {"payload": {"fileList": [{"fileName": "recordings/file.mp4"}]}}
                ]
            }
        }
        rec = Recording.objects.create(
            webinar=self.webinar, status=Recording.RECORDING_STATUS, resource_id="res", sid="sid"
        )
        from ..api.views import _stop_recording

        _stop_recording(rec)
        rec.refresh_from_db()
        self.assertEqual(rec.status, Recording.PROCESSING_STATUS)
        self.assertEqual(rec.recording_url, "recordings/file.mp4")
        self.assertEqual(rec.kinescope_upload_status, "pending")
        mock_upload.assert_called_once_with(str(rec.recording_id))

    @patch("apps.webinars.tasks.upload_recording_to_kinescope.delay")
    @patch("apps.webinars.api.views.recording_stop_web")
    def test_stop_recording_handles_agora_error_gracefully(self, mock_stop, mock_upload):
        mock_stop.side_effect = Exception("agora down")
        rec = Recording.objects.create(
            webinar=self.webinar, status=Recording.RECORDING_STATUS, resource_id="res", sid="sid"
        )
        from ..api.views import _stop_recording

        _stop_recording(rec)
        rec.refresh_from_db()
        self.assertEqual(rec.status, Recording.PROCESSING_STATUS)
        self.assertEqual(rec.recording_url, "")
        mock_upload.assert_not_called()

    @patch("apps.webinars.tasks.upload_recording_to_kinescope.delay")
    def test_stop_recording_skips_agora_when_no_resource_id(self, mock_upload):
        rec = Recording.objects.create(webinar=self.webinar, status=Recording.RECORDING_STATUS)
        from ..api.views import _stop_recording

        _stop_recording(rec)
        rec.refresh_from_db()
        self.assertEqual(rec.status, Recording.PROCESSING_STATUS)
        mock_upload.assert_not_called()


class ExtractRecordingUrlTest(BaseWebinarTestCase):

    def _extract(self, payload):
        from ..api.views import _extract_recording_url

        return _extract_recording_url(payload)

    def test_camel_case_filename_in_extension_service(self):
        url = self._extract(
            {
                "serverResponse": {
                    "extensionServiceState": [
                        {"payload": {"fileList": [{"fileName": "rec/a.mp4"}]}}
                    ]
                }
            }
        )
        self.assertEqual(url, "rec/a.mp4")

    def test_lowercase_filename_in_extension_service(self):
        url = self._extract(
            {
                "serverResponse": {
                    "extensionServiceState": [
                        {"payload": {"fileList": [{"filename": "rec/a.mp4"}]}}
                    ]
                }
            }
        )
        self.assertEqual(url, "rec/a.mp4")

    def test_prefers_mp4_over_m3u8(self):
        url = self._extract(
            {
                "serverResponse": {
                    "extensionServiceState": [
                        {
                            "payload": {
                                "fileList": [
                                    {"filename": "rec/a.m3u8"},
                                    {"filename": "rec/a_0.mp4"},
                                ]
                            }
                        }
                    ]
                }
            }
        )
        self.assertEqual(url, "rec/a_0.mp4")

    def test_real_agora_response_with_multiple_services(self):
        url = self._extract(
            {
                "serverResponse": {
                    "extensionServiceState": [
                        {
                            "payload": {
                                "fileList": [
                                    {"filename": "b0c07c_webinar.m3u8", "sliceStartTime": 1},
                                    {"filename": "b0c07c_webinar_0.mp4", "sliceStartTime": 1},
                                ]
                            },
                            "serviceName": "web_recorder_service",
                        },
                        {
                            "payload": {"uploadingStatus": "backuped"},
                            "serviceName": "upload_service",
                        },
                    ]
                }
            }
        )
        self.assertEqual(url, "b0c07c_webinar_0.mp4")

    def test_top_level_file_list(self):
        url = self._extract({"serverResponse": {"fileList": [{"filename": "rec/x.mp4"}]}})
        self.assertEqual(url, "rec/x.mp4")

    def test_returns_first_when_no_mp4(self):
        url = self._extract(
            {
                "serverResponse": {
                    "extensionServiceState": [
                        {"payload": {"fileList": [{"filename": "rec/a.m3u8"}]}}
                    ]
                }
            }
        )
        self.assertEqual(url, "rec/a.m3u8")

    def test_empty_response_returns_empty(self):
        self.assertEqual(self._extract({}), "")
        self.assertEqual(self._extract({"serverResponse": {}}), "")


class RecordingPdfViewTest(WebinarEndpointsBase):

    def setUp(self):
        super().setUp()
        self.webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.recording = Recording.objects.create(webinar=self.webinar)

    def test_student_forbidden_to_post(self):
        self.authenticate(self.student)
        response = self.client.post(self.url_pdf(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_without_screenshots_returns_400(self):
        self.authenticate(self.teacher)
        response = self.client.post(self.url_pdf(self.recording.recording_id), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.webinars.api.views.img2pdf.convert", return_value=b"%PDF-1.4 fake")
    def test_post_with_screenshots_saves_pdf(self, mock_convert):
        from unittest.mock import MagicMock

        from django.core.files.uploadedfile import SimpleUploadedFile

        mock_asset = MagicMock()
        mock_asset.asset_id = "fake-asset-id"
        mock_upload_api = MagicMock()
        mock_upload_api.upload_server_side.return_value = mock_asset
        mock_binding_api = MagicMock()
        screenshot = SimpleUploadedFile("a.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        self.authenticate(self.teacher)
        with (
            patch("apps.webinars.api.views.build_upload_api", return_value=mock_upload_api),
            patch("apps.webinars.api.views.build_binding_api", return_value=mock_binding_api),
        ):
            response = self.client.post(
                self.url_pdf(self.recording.recording_id),
                {"screenshots": [screenshot]},
                format="multipart",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_upload_api.upload_server_side.assert_called_once()
        mock_binding_api.sync_single.assert_called_once()

    def test_post_returns_404_for_nonexistent_recording(self):
        import uuid

        self.authenticate(self.teacher)
        response = self.client.post(self.url_pdf(uuid.uuid4()), format="multipart")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_returns_404_for_soft_deleted_recording(self):
        self.recording.is_deleted = True
        self.recording.save()
        from django.core.files.uploadedfile import SimpleUploadedFile

        screenshot = SimpleUploadedFile("a.png", b"\x89PNG", content_type="image/png")
        self.authenticate(self.teacher)
        response = self.client.post(
            self.url_pdf(self.recording.recording_id),
            {"screenshots": [screenshot]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_pdf_as_author(self):
        self.recording.whiteboard_pdf_url = (
            "https://storage.yandexcloud.net/bucket/whiteboards/x.pdf"
        )
        self.recording.save()
        self.authenticate(self.teacher)
        response = self.client.delete(self.url_pdf(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.recording.refresh_from_db()
        self.assertEqual(self.recording.whiteboard_pdf_url, "")

    def test_delete_pdf_is_idempotent_when_no_pdf(self):
        self.authenticate(self.teacher)
        response = self.client.delete(self.url_pdf(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_forbidden_for_student(self):
        self.authenticate(self.student)
        response = self.client.delete(self.url_pdf(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RecordingDeleteViewTest(WebinarEndpointsBase):

    def setUp(self):
        super().setUp()
        self.webinar = Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.recording = Recording.objects.create(webinar=self.webinar)

    def test_student_forbidden(self):
        self.authenticate(self.student)
        response = self.client.delete(self.url_rec_delete(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_soft_deletes_recording(self):
        self.authenticate(self.teacher)
        response = self.client.delete(self.url_rec_delete(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.recording.refresh_from_db()
        self.assertTrue(self.recording.is_deleted)
        self.assertIsNotNone(self.recording.deleted_at)
        self.assertEqual(self.recording.deleted_by, self.teacher)

    def test_moderator_can_delete(self):
        self.authenticate(self.moderator)
        response = self.client.delete(self.url_rec_delete(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_delete_already_deleted_recording(self):
        self.recording.is_deleted = True
        self.recording.save()
        self.authenticate(self.teacher)
        response = self.client.delete(self.url_rec_delete(self.recording.recording_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_404_for_recording_in_different_lesson(self):
        other_lesson = create_test_lesson(self.section, title="Другой урок")
        other_webinar = Webinar.objects.create(lesson=other_lesson)
        other_rec = Recording.objects.create(webinar=other_webinar)
        self.authenticate(self.teacher)
        response = self.client.delete(self.url_rec_delete(other_rec.recording_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class KinescopeDRMAuthViewTest(BaseWebinarTestCase):
    URL = "/api/v1/kinescope/drm-auth/"

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.teacher = create_test_user(email="t_drm@test.com", role="teacher")
        self.student = create_test_user(email="s_drm@test.com", role="student")
        self.course = create_test_course()
        self.course.authors.add(self.teacher)
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.webinar = Webinar.objects.create(lesson=self.lesson)
        self.recording = Recording.objects.create(webinar=self.webinar, kinescope_video_id="vid-42")
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "KINESCOPE_DRM_AUTH_USERNAME": self.VALID_USER,
                "KINESCOPE_DRM_AUTH_PASSWORD": self.VALID_SECRET,
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        super().tearDown()

    VALID_USER = "drm-user-test"
    VALID_SECRET = "drm-secret-test"

    def _basic_auth(self, user=None, pwd=None):
        user = user or self.VALID_USER
        pwd = pwd or self.VALID_SECRET
        creds = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        return f"Basic {creds}"

    def _make_drm_token(self, user_id, video_id):
        import jwt
        from django.conf import settings as dj_settings

        return jwt.encode(
            {"user_id": str(user_id), "video_id": video_id},
            dj_settings.SECRET_KEY,
            algorithm="HS256",
        )

    def test_missing_auth_header_returns_403(self):
        response = self.client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_basic_auth_returns_403(self):
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": "whatever"},
            HTTP_AUTHORIZATION=self._basic_auth(user="bad-user", pwd="bad-value"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_malformed_basic_auth_returns_403(self):
        response = self.client.post(
            self.URL,
            {"id": "v", "token": "t"},
            HTTP_AUTHORIZATION="Basic not-base64",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_video_id_or_token_returns_403(self):
        response = self.client.post(
            self.URL, {"id": "", "token": ""}, HTTP_AUTHORIZATION=self._basic_auth(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_jwt_returns_403(self):
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": "not-a-jwt"},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_token_video_mismatch_returns_403(self):
        token = self._make_drm_token(self.teacher.pk, "other-video")
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_recording_for_video_returns_403(self):
        token = self._make_drm_token(self.teacher.pk, "unknown-video")
        response = self.client.post(
            self.URL,
            {"id": "unknown-video", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_soft_deleted_recording_returns_403(self):
        self.recording.is_deleted = True
        self.recording.save()
        token = self._make_drm_token(self.teacher.pk, "vid-42")
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_user_returns_403(self):
        token = self._make_drm_token(999999, "vid-42")
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_author_gets_200(self):
        token = self._make_drm_token(self.teacher.pk, "vid-42")
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_enrolled_student_gets_200(self):
        from datetime import timedelta

        payment = Payment.objects.create(user=self.student, total_sum=1000, status="success")
        CourseEnrollment.objects.create(
            user=self.student,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )
        token = self._make_drm_token(self.student.pk, "vid-42")
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_enrolled_student_gets_403(self):
        token = self._make_drm_token(self.student.pk, "vid-42")
        response = self.client.post(
            self.URL,
            {"id": "vid-42", "token": token},
            HTTP_AUTHORIZATION=self._basic_auth(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_basic_prefix_returns_403(self):
        response = self.client.post(
            self.URL, {"id": "v", "token": "t"}, HTTP_AUTHORIZATION="Bearer abc", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WebinarStartIdempotencyTest(WebinarEndpointsBase):

    @patch("apps.webinars.api.views.create_whiteboard_room", return_value="room")
    def test_get_or_create_does_not_duplicate_webinar(self, _mock_create):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.ENDED_STATUS)
        self.authenticate(self.teacher)
        response = self.client.post(self.url_start())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Webinar.objects.filter(lesson=self.lesson).count(), 1)


@patch("apps.notifications.tasks.send_course_notification")
@patch("apps.notifications.tasks.send_webinar_scheduled_notification")
@patch("apps.webinars.signals.invalidate_lesson_detail_cache")
class WebinarScheduleViewTest(WebinarEndpointsBase):
    SCHEDULE_PAYLOAD = {"scheduled_at": "2026-06-01T18:00:00Z"}

    def test_requires_authentication(self, *_):
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_schedule(self, *_):
        self.authenticate(self.student)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_teacher_cannot_schedule(self, *_):
        self.authenticate(self.other_teacher)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_creates_webinar_and_sets_scheduled_at(
        self, mock_invalidate, mock_webinar_notify, mock_course_notify, *_
    ):
        self.authenticate(self.teacher)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        webinar = Webinar.objects.get(lesson=self.lesson)
        self.assertIsNotNone(webinar.scheduled_at)
        self.assertEqual(response.data["webinar_id"], str(webinar.webinar_id))
        self.assertEqual(webinar.status, Webinar.PENDING_STATUS)
        mock_invalidate.assert_called_with(self.course.slug, self.lesson.slug)
        self.assertEqual(mock_invalidate.call_count, 2)
        mock_webinar_notify.delay.assert_called_once()
        mock_course_notify.delay.assert_not_called()
        title = mock_webinar_notify.delay.call_args.kwargs["title"]
        self.assertIn("Назначен вебинар", title)

    def test_moderator_can_schedule(self, *_):
        self.authenticate(self.moderator)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_existing_pending_update_sends_change_notification(
        self, mock_invalidate, mock_webinar_notify, mock_course_notify, *_
    ):
        Webinar.objects.create(
            lesson=self.lesson, scheduled_at=timezone.now(), status=Webinar.PENDING_STATUS
        )
        self.authenticate(self.teacher)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_webinar_notify.delay.assert_called_once()
        mock_course_notify.delay.assert_not_called()
        title = mock_webinar_notify.delay.call_args.kwargs["title"]
        self.assertIn("Время вебинара изменено", title)

    def test_clearing_schedule_sends_cancel_notification(
        self, mock_invalidate, mock_webinar_notify, mock_course_notify, *_
    ):
        Webinar.objects.create(
            lesson=self.lesson, scheduled_at=timezone.now(), status=Webinar.PENDING_STATUS
        )
        self.authenticate(self.teacher)
        response = self.client.patch(self.url_schedule(), {"scheduled_at": None}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        webinar = Webinar.objects.get(lesson=self.lesson)
        self.assertIsNone(webinar.scheduled_at)
        mock_course_notify.delay.assert_called_once()
        mock_webinar_notify.delay.assert_not_called()
        title = mock_course_notify.delay.call_args.args[1]
        self.assertIn("Вебинар отменён", title)

    def test_live_webinar_returns_409(self, *_):
        Webinar.objects.create(lesson=self.lesson, status=Webinar.LIVE_STATUS)
        self.authenticate(self.teacher)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_ended_webinar_is_reset_to_pending(self, *_):
        Webinar.objects.create(
            lesson=self.lesson, status=Webinar.ENDED_STATUS, ended_at=timezone.now()
        )
        self.authenticate(self.teacher)
        response = self.client.patch(self.url_schedule(), self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        webinar = Webinar.objects.get(lesson=self.lesson)
        self.assertEqual(webinar.status, Webinar.PENDING_STATUS)
        self.assertIsNone(webinar.ended_at)

    def test_invalid_payload_returns_400(self, *_):
        self.authenticate(self.teacher)
        response = self.client.patch(
            self.url_schedule(), {"scheduled_at": "not-a-date"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_404_for_nonexistent_lesson(self, *_):
        self.authenticate(self.teacher)
        url = f"/api/v1/courses/{self.course.slug}/lessons/missing-lesson/webinar/schedule/"
        response = self.client.patch(url, self.SCHEDULE_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
