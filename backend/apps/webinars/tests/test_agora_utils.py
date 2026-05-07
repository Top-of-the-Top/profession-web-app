import time
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from ..api.utils.agora_utils import (
    ROLE_PUBLISHER,
    ROLE_SUBSCRIBER,
    ban_whiteboard_room,
    create_whiteboard_room,
    generate_rtm_token,
    generate_whiteboard_room_token,
    get_channel_user_count,
    make_recorder_token,
    recording_acquire,
    recording_start,
    recording_start_web,
    recording_stop,
    recording_stop_web,
    user_uid_from_uuid,
    verify_recorder_token,
)


class UserUidFromUuidTest(SimpleTestCase):

    def test_returns_integer(self):
        uid = user_uid_from_uuid("some-uuid")
        self.assertIsInstance(uid, int)

    def test_uid_is_within_int32_range(self):
        uid = user_uid_from_uuid("some-uuid-value")
        self.assertGreaterEqual(uid, 1)
        self.assertLessEqual(uid, 2**31)

    def test_uid_stable_for_same_input(self):
        self.assertEqual(
            user_uid_from_uuid("aaa-bbb"),
            user_uid_from_uuid("aaa-bbb"),
        )

    def test_uid_differs_for_different_inputs(self):
        self.assertNotEqual(
            user_uid_from_uuid("aaa"),
            user_uid_from_uuid("bbb"),
        )

    def test_role_constants_are_distinct(self):
        self.assertNotEqual(ROLE_PUBLISHER, ROLE_SUBSCRIBER)


@override_settings(SECRET_KEY="test-secret-key")
class RecorderTokenTest(SimpleTestCase):

    def test_make_and_verify_round_trip(self):
        token = make_recorder_token("webinar-123")
        self.assertEqual(verify_recorder_token(token), "webinar-123")

    def test_token_has_three_parts(self):
        token = make_recorder_token("w-1")
        self.assertEqual(len(token.split(":")), 3)

    def test_verify_rejects_malformed_token(self):
        self.assertIsNone(verify_recorder_token("bad"))
        self.assertIsNone(verify_recorder_token("a:b"))
        self.assertIsNone(verify_recorder_token("a:b:c:d"))

    def test_verify_rejects_expired_token(self):
        expired = int(time.time()) - 10
        msg = f"webinar-1:{expired}"
        import hashlib
        import hmac

        from django.conf import settings

        sig = hmac.new(
            settings.SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()
        token = f"{msg}:{sig}"
        self.assertIsNone(verify_recorder_token(token))

    def test_verify_rejects_tampered_signature(self):
        token = make_recorder_token("w-1")
        parts = token.split(":")
        parts[2] = "a" * len(parts[2])
        tampered = ":".join(parts)
        self.assertIsNone(verify_recorder_token(tampered))

    def test_verify_rejects_tampered_payload(self):
        token = make_recorder_token("w-1")
        parts = token.split(":")
        parts[0] = "w-2"
        tampered = ":".join(parts)
        self.assertIsNone(verify_recorder_token(tampered))

    @override_settings(SECRET_KEY="different-secret")
    def test_verify_rejects_token_signed_with_different_secret(self):
        with override_settings(SECRET_KEY="secret-a"):
            token = make_recorder_token("w-1")
        with override_settings(SECRET_KEY="secret-b"):
            self.assertIsNone(verify_recorder_token(token))


class GetChannelUserCountTest(SimpleTestCase):

    def _mock_response(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        return resp

    @patch("apps.webinars.api.utils.agora_utils.requests.get")
    def test_returns_zero_when_channel_does_not_exist(self, mock_get):
        mock_get.return_value = self._mock_response({"data": {"channel_exist": False}})
        self.assertEqual(get_channel_user_count("ch"), 0)

    @patch("apps.webinars.api.utils.agora_utils.requests.get")
    def test_returns_user_count_excluding_recorder(self, mock_get):
        mock_get.return_value = self._mock_response(
            {
                "data": {
                    "channel_exist": True,
                    "users": [1, 2, 3, 999999],
                },
            }
        )
        self.assertEqual(get_channel_user_count("ch"), 3)

    @patch("apps.webinars.api.utils.agora_utils.requests.get")
    def test_returns_zero_for_channel_with_only_recorder(self, mock_get):
        mock_get.return_value = self._mock_response(
            {
                "data": {
                    "channel_exist": True,
                    "users": [999999],
                },
            }
        )
        self.assertEqual(get_channel_user_count("ch"), 0)

    @patch("apps.webinars.api.utils.agora_utils.requests.get")
    def test_returns_zero_for_channel_with_no_users(self, mock_get):
        mock_get.return_value = self._mock_response(
            {
                "data": {"channel_exist": True, "users": []},
            }
        )
        self.assertEqual(get_channel_user_count("ch"), 0)

    @patch("apps.webinars.api.utils.agora_utils.requests.get")
    def test_raises_on_http_error(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("500")
        mock_get.return_value = resp

        with self.assertRaises(Exception):
            get_channel_user_count("ch")


class WhiteboardApiTest(SimpleTestCase):

    def _token_response(self, text='"sdk-token"'):
        resp = MagicMock()
        resp.text = text
        resp.raise_for_status.return_value = None
        return resp

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_create_whiteboard_room_returns_uuid(self, mock_post):
        token_resp = self._token_response()
        room_resp = MagicMock()
        room_resp.json.return_value = {"uuid": "room-uuid-xyz"}
        room_resp.raise_for_status.return_value = None
        mock_post.side_effect = [token_resp, room_resp]

        result = create_whiteboard_room()

        self.assertEqual(result, "room-uuid-xyz")
        self.assertEqual(mock_post.call_count, 2)

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_generate_whiteboard_room_token_strips_quotes(self, mock_post):
        token_resp = self._token_response()
        room_token_resp = MagicMock()
        room_token_resp.text = '"wb-room-token"'
        room_token_resp.raise_for_status.return_value = None
        mock_post.side_effect = [token_resp, room_token_resp]

        result = generate_whiteboard_room_token("room", role="writer")
        self.assertEqual(result, "wb-room-token")

    @patch("apps.webinars.api.utils.agora_utils.requests.patch")
    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_ban_whiteboard_room_calls_netless_patch(self, mock_post, mock_patch):
        mock_post.return_value = self._token_response()
        patch_resp = MagicMock()
        patch_resp.raise_for_status.return_value = None
        mock_patch.return_value = patch_resp

        ban_whiteboard_room("room-1")

        mock_patch.assert_called_once()
        args, kwargs = mock_patch.call_args
        self.assertIn("room-1", args[0])
        self.assertEqual(kwargs["json"], {"isBan": True})


class RecordingApiTest(SimpleTestCase):

    def _resp(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        return resp

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_recording_acquire_returns_resource_id(self, mock_post):
        mock_post.return_value = self._resp({"resourceId": "res-1"})
        self.assertEqual(recording_acquire("ch", "1"), "res-1")

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_recording_start_returns_sid(self, mock_post):
        mock_post.return_value = self._resp({"sid": "sid-1"})
        self.assertEqual(recording_start("ch", "1", "res", "tok"), "sid-1")

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_recording_start_web_returns_sid(self, mock_post):
        mock_post.return_value = self._resp({"sid": "web-sid"})
        self.assertEqual(
            recording_start_web("ch", "1", "res", "http://rec"),
            "web-sid",
        )

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_recording_stop_returns_json(self, mock_post):
        payload = {"serverResponse": {"extensionServiceState": []}}
        mock_post.return_value = self._resp(payload)
        self.assertEqual(recording_stop("ch", "1", "res", "sid"), payload)

    @patch("apps.webinars.api.utils.agora_utils.requests.post")
    def test_recording_stop_web_returns_json(self, mock_post):
        payload = {"serverResponse": {}}
        mock_post.return_value = self._resp(payload)
        self.assertEqual(recording_stop_web("ch", "1", "res", "sid"), payload)


@patch.dict(
    "os.environ",
    {
        "AGORA_APP_ID": "app-id-test",
        "AGORA_APP_CERTIFICATE": "app-cert-test",
    },
)
class GenerateRtmTokenTest(SimpleTestCase):

    @patch(
        "apps.webinars.api.utils.agora_utils.RtmTokenBuilder.buildToken", return_value="rtm-token"
    )
    def test_returns_token_from_builder(self, mock_build):
        self.assertEqual(generate_rtm_token(12345), "rtm-token")

    @patch(
        "apps.webinars.api.utils.agora_utils.RtmTokenBuilder.buildToken", return_value="rtm-token"
    )
    def test_passes_app_id_and_certificate(self, mock_build):
        generate_rtm_token(12345)
        args = mock_build.call_args[0]
        self.assertEqual(args[0], "app-id-test")
        self.assertEqual(args[1], "app-cert-test")

    @patch(
        "apps.webinars.api.utils.agora_utils.RtmTokenBuilder.buildToken", return_value="rtm-token"
    )
    def test_passes_user_account_as_string(self, mock_build):
        generate_rtm_token(12345)
        args = mock_build.call_args[0]
        self.assertEqual(args[2], "12345")

    @patch(
        "apps.webinars.api.utils.agora_utils.RtmTokenBuilder.buildToken", return_value="rtm-token"
    )
    def test_passes_role_rtm_user(self, mock_build):
        generate_rtm_token(12345)
        args = mock_build.call_args[0]
        self.assertEqual(args[3], 1)

    @patch(
        "apps.webinars.api.utils.agora_utils.RtmTokenBuilder.buildToken", return_value="rtm-token"
    )
    def test_expiration_in_future(self, mock_build):
        generate_rtm_token(12345)
        args = mock_build.call_args[0]
        privilege_expired_ts = args[4]
        self.assertGreater(privilege_expired_ts, int(time.time()))
