from django.test import RequestFactory
from unittest.mock import patch, MagicMock

from ..api.serializers import (
    WebinarSerializer,
    WebinarTokenSerializer,
    RecordingListItemSerializer,
)
from ..models import Webinar, Recording
from .test_models import (
    BaseWebinarTestCase,
    create_test_user,
    create_test_course,
    create_test_section,
    create_test_lesson,
)


class WebinarSerializerTest(BaseWebinarTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.user = create_test_user(role='teacher')

    def test_serializer_exposes_expected_fields(self):
        webinar = Webinar.objects.create(lesson=self.lesson)
        data = WebinarSerializer(webinar).data

        self.assertIn('webinar_id', data)
        self.assertIn('lesson', data)
        self.assertIn('status', data)
        self.assertIn('started_by', data)
        self.assertIn('started_at', data)
        self.assertIn('ended_at', data)

    def test_read_only_fields_ignored_on_input(self):
        serializer = WebinarSerializer(data={
            'lesson': self.lesson.lesson_id,
            'webinar_id': '00000000-0000-0000-0000-000000000000',
            'started_by': self.user.pk,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()

        self.assertNotEqual(str(instance.webinar_id), '00000000-0000-0000-0000-000000000000')
        self.assertIsNone(instance.started_by)


class WebinarTokenSerializerTest(BaseWebinarTestCase):

    def test_all_required_fields_present(self):
        data = {
            'rtc_token': 'tok',
            'agora_app_id': 'app',
            'channel_name': 'ch',
            'uid': 42,
            'whiteboard_app_id': 'wb',
            'whiteboard_room_uuid': 'room',
            'whiteboard_room_token': 'wbtok',
            'whiteboard_region': 'eu',
            'role': 'teacher',
        }
        serializer = WebinarTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_field_is_invalid(self):
        serializer = WebinarTokenSerializer(data={'rtc_token': 'tok'})
        self.assertFalse(serializer.is_valid())

    def test_uid_must_be_integer(self):
        serializer = WebinarTokenSerializer(data={
            'rtc_token': 'tok',
            'agora_app_id': 'app',
            'channel_name': 'ch',
            'uid': 'not-an-int',
            'whiteboard_app_id': 'wb',
            'whiteboard_room_uuid': 'room',
            'whiteboard_room_token': 'wbtok',
            'whiteboard_region': 'eu',
            'role': 'teacher',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('uid', serializer.errors)


class RecordingListItemSerializerTest(BaseWebinarTestCase):

    def setUp(self):
        super().setUp()
        self.course = create_test_course()
        self.section = create_test_section(self.course)
        self.lesson = create_test_lesson(self.section)
        self.webinar = Webinar.objects.create(lesson=self.lesson)
        self.factory = RequestFactory()

    def _request_with_user(self, user=None, authenticated=True):
        request = self.factory.get('/')
        if user is None:
            user = MagicMock()
            user.is_authenticated = authenticated
            user.pk = 1
        request.user = user
        return request

    def test_embed_url_empty_when_not_ready(self):
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_upload_status='processing',
            kinescope_video_id='vid123',
        )
        request = self._request_with_user()
        data = RecordingListItemSerializer(rec, context={'request': request}).data

        self.assertEqual(data['kinescope_embed_url'], '')

    def test_embed_url_empty_when_no_video_id(self):
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_upload_status='ready',
            kinescope_video_id='',
        )
        request = self._request_with_user()
        data = RecordingListItemSerializer(rec, context={'request': request}).data

        self.assertEqual(data['kinescope_embed_url'], '')

    def test_embed_url_empty_without_request_in_context(self):
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_upload_status='ready',
            kinescope_video_id='vid123',
        )
        data = RecordingListItemSerializer(rec, context={}).data
        self.assertEqual(data['kinescope_embed_url'], '')

    def test_embed_url_empty_when_user_not_authenticated(self):
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_upload_status='ready',
            kinescope_video_id='vid123',
        )
        request = self._request_with_user(authenticated=False)
        data = RecordingListItemSerializer(rec, context={'request': request}).data

        self.assertEqual(data['kinescope_embed_url'], '')

    @patch('apps.webinars.api.utils.kinescope_utils.generate_drm_token')
    def test_embed_url_generated_for_ready_recording(self, mock_token):
        mock_token.return_value = 'drm-token-123'
        rec = Recording.objects.create(
            webinar=self.webinar,
            kinescope_upload_status='ready',
            kinescope_video_id='vid123',
        )
        request = self._request_with_user()
        data = RecordingListItemSerializer(rec, context={'request': request}).data

        self.assertIn('kinescope.io/embed/vid123', data['kinescope_embed_url'])
        self.assertIn('drmauthtoken=drm-token-123', data['kinescope_embed_url'])
        mock_token.assert_called_once()
