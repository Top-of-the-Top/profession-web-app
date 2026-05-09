import time
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ..api.utils.kinescope_utils import (
    create_folder,
    generate_drm_token,
    get_video_status,
    setup_drm_auth,
    upload_video_by_url,
)


@override_settings(SECRET_KEY="test-secret", KINESCOPE_API_TOKEN="tok", KINESCOPE_PROJECT_ID="proj")
class GenerateDrmTokenTest(SimpleTestCase):

    def test_token_is_jwt_with_expected_payload(self):
        import jwt

        token = generate_drm_token(user_id=42, video_id="vid-1")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        self.assertEqual(payload["user_id"], "42")
        self.assertEqual(payload["video_id"], "vid-1")
        self.assertEqual(payload["token_type"], "kinescope_drm")
        self.assertIn("exp", payload)

    def test_token_user_id_is_string(self):
        import jwt

        token = generate_drm_token(user_id=123, video_id="v")
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        self.assertIsInstance(payload["user_id"], str)

    def test_token_expiration_respects_lifetime(self):
        import jwt

        before = int(time.time())
        token = generate_drm_token(user_id=1, video_id="v", lifetime_seconds=60)
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        self.assertGreaterEqual(payload["exp"], before + 60)
        self.assertLessEqual(payload["exp"], before + 120)

    def test_token_invalid_with_wrong_secret(self):
        import jwt

        token = generate_drm_token(user_id=1, video_id="v")
        with self.assertRaises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])


@override_settings(SECRET_KEY="test-secret", KINESCOPE_API_TOKEN="tok", KINESCOPE_PROJECT_ID="proj")
class KinescopeApiTest(SimpleTestCase):

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._post")
    def test_create_folder_returns_id(self, mock_post):
        mock_post.return_value = {"data": {"id": "folder-1"}}
        self.assertEqual(create_folder("name", project_id="proj"), "folder-1")

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._post")
    def test_create_folder_returns_empty_if_missing(self, mock_post):
        mock_post.return_value = {"data": {}}
        self.assertEqual(create_folder("name", project_id="proj"), "")

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._post")
    def test_upload_video_by_url_returns_data(self, mock_post):
        mock_post.return_value = {"data": {"id": "v-1"}}
        result = upload_video_by_url("http://u", "title", parent_id="parent")
        self.assertEqual(result, {"id": "v-1"})

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._post")
    def test_upload_video_by_url_passes_expected_headers(self, mock_post):
        mock_post.return_value = {"data": {"id": "stub-id"}}
        upload_video_by_url("http://video-url", "My Title", parent_id="parent-xyz")
        _, kwargs = mock_post.call_args
        headers = kwargs["extra_headers"]
        self.assertEqual(headers["X-Video-URL"], "http://video-url")
        self.assertEqual(headers["X-Video-Title"], "My%20Title")
        self.assertEqual(headers["X-Parent-ID"], "parent-xyz")
        self.assertTrue(kwargs.get("strip_json_content_type"))

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._post")
    def test_upload_video_by_url_encodes_cyrillic_title(self, mock_post):
        mock_post.return_value = {"data": {"id": "stub-id"}}
        upload_video_by_url("http://video-url", "Вебинар: Урок", parent_id="p")
        _, kwargs = mock_post.call_args
        title = kwargs["extra_headers"]["X-Video-Title"]
        self.assertTrue(all((ord(c) < 128 for c in title)), f"Title содержит non-ASCII: {title}")
        self.assertIn("%D0%92", title)

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._get")
    def test_get_video_status_returns_data(self, mock_get):
        mock_get.return_value = {"data": {"status": "ready"}}
        self.assertEqual(get_video_status("v-1"), {"status": "ready"})

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._get")
    def test_get_video_status_returns_empty_dict_if_missing(self, mock_get):
        mock_get.return_value = {}
        self.assertEqual(get_video_status("v-1"), {})

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._put_json")
    def test_setup_drm_auth_passes_payload(self, mock_put):
        mock_put.return_value = {"ok": True}
        setup_drm_auth("http://cb", "user", "pass", strict=False)
        args, kwargs = mock_put.call_args
        self.assertEqual(args[0], "/drm/auth")
        payload = args[1]
        self.assertEqual(payload["url"], "http://cb")
        self.assertEqual(payload["username"], "user")
        self.assertEqual(payload["password"], "pass")
        self.assertFalse(payload["strict"])

    @patch("apps.core.meta_management.storages.kinescope.KinescopeBackend._post")
    def test_create_folder_raises_on_http_error(self, mock_post):
        mock_post.side_effect = Exception("500")
        with self.assertRaises(Exception):
            create_folder("name", project_id="proj")
