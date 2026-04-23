import time
from django.test import SimpleTestCase, override_settings
from unittest.mock import patch, MagicMock

from ..api.utils import kinescope_utils
from ..api.utils.kinescope_utils import (
    generate_drm_token,
    create_folder,
    upload_video_by_url,
    get_video_status,
    setup_drm_auth,
)


@override_settings(SECRET_KEY='test-secret')
class GenerateDrmTokenTest(SimpleTestCase):

    def test_token_is_jwt_with_expected_payload(self):
        import jwt
        token = generate_drm_token(user_id=42, video_id='vid-1')
        payload = jwt.decode(token, 'test-secret', algorithms=['HS256'])

        self.assertEqual(payload['user_id'], '42')
        self.assertEqual(payload['video_id'], 'vid-1')
        self.assertEqual(payload['token_type'], 'kinescope_drm')
        self.assertIn('exp', payload)

    def test_token_user_id_is_string(self):
        import jwt
        token = generate_drm_token(user_id=123, video_id='v')
        payload = jwt.decode(token, 'test-secret', algorithms=['HS256'])
        self.assertIsInstance(payload['user_id'], str)

    def test_token_expiration_respects_lifetime(self):
        import jwt
        before = int(time.time())
        token = generate_drm_token(user_id=1, video_id='v', lifetime_seconds=60)
        payload = jwt.decode(token, 'test-secret', algorithms=['HS256'])

        self.assertGreaterEqual(payload['exp'], before + 60)
        self.assertLessEqual(payload['exp'], before + 120)

    def test_token_invalid_with_wrong_secret(self):
        import jwt
        token = generate_drm_token(user_id=1, video_id='v')
        with self.assertRaises(jwt.InvalidSignatureError):
            jwt.decode(token, 'wrong-secret', algorithms=['HS256'])


class KinescopeApiTest(SimpleTestCase):

    def _json_resp(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        return resp

    @patch('apps.webinars.api.utils.kinescope_utils.requests.post')
    def test_create_folder_returns_id(self, mock_post):
        mock_post.return_value = self._json_resp({'data': {'id': 'folder-1'}})
        self.assertEqual(create_folder('name', project_id='proj'), 'folder-1')

    @patch('apps.webinars.api.utils.kinescope_utils.requests.post')
    def test_create_folder_returns_empty_if_missing(self, mock_post):
        mock_post.return_value = self._json_resp({'data': {}})
        self.assertEqual(create_folder('name', project_id='proj'), '')

    @patch('apps.webinars.api.utils.kinescope_utils.requests.post')
    def test_upload_video_by_url_returns_data(self, mock_post):
        mock_post.return_value = self._json_resp({'data': {'id': 'v-1'}})
        result = upload_video_by_url('http://u', 'title', parent_id='parent')
        self.assertEqual(result, {'id': 'v-1'})

    @patch('apps.webinars.api.utils.kinescope_utils.requests.post')
    def test_upload_video_by_url_passes_expected_headers(self, mock_post):
        mock_post.return_value = self._json_resp({'data': {}})
        upload_video_by_url('http://video-url', 'My Title', parent_id='parent-xyz')

        _, kwargs = mock_post.call_args
        headers = kwargs['headers']
        self.assertEqual(headers['X-Video-URL'], 'http://video-url')
        self.assertEqual(headers['X-Video-Title'], 'My Title')
        self.assertEqual(headers['X-Parent-ID'], 'parent-xyz')

    @patch('apps.webinars.api.utils.kinescope_utils.requests.get')
    def test_get_video_status_returns_data(self, mock_get):
        mock_get.return_value = self._json_resp({'data': {'status': 'ready'}})
        self.assertEqual(get_video_status('v-1'), {'status': 'ready'})

    @patch('apps.webinars.api.utils.kinescope_utils.requests.get')
    def test_get_video_status_returns_empty_dict_if_missing(self, mock_get):
        mock_get.return_value = self._json_resp({})
        self.assertEqual(get_video_status('v-1'), {})

    @patch('apps.webinars.api.utils.kinescope_utils.requests.put')
    def test_setup_drm_auth_passes_payload(self, mock_put):
        mock_put.return_value = self._json_resp({'ok': True})
        setup_drm_auth('http://cb', 'user', 'pass', strict=False)

        _, kwargs = mock_put.call_args
        self.assertEqual(kwargs['json']['url'], 'http://cb')
        self.assertEqual(kwargs['json']['username'], 'user')
        self.assertEqual(kwargs['json']['password'], 'pass')
        self.assertFalse(kwargs['json']['strict'])

    @patch('apps.webinars.api.utils.kinescope_utils.requests.post')
    def test_create_folder_raises_on_http_error(self, mock_post):
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception('500')
        mock_post.return_value = resp

        with self.assertRaises(Exception):
            create_folder('name', project_id='proj')
