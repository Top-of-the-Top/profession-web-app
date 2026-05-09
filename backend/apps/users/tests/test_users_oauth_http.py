import uuid
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.api.utils.crypto_utils import encrypt_data
from apps.users.models import User

_OAUTH_SETTINGS = dict(
    FRONTEND_OAUTH_YANDEX_REDIRECT_URI="http://frontend.test/yandex",
    FRONTEND_OAUTH_VK_REDIRECT_URI="http://frontend.test/vk",
    YANDEX_CLIENT_ID="test_yandex_id",
    YANDEX_CLIENT_SECRET="test_yandex_secret",
    VK_CLIENT_ID="test_vk_id",
    VK_CLIENT_SECRET="test_vk_secret",
    VK_REDIRECT_URI="http://backend.test/vk/callback",
)


def _yandex_httpx_mocks(suffix: str):
    token_resp = MagicMock(status_code=200)
    token_resp.json.return_value = {"access_token": "ya-access"}
    info_resp = MagicMock(status_code=200)
    info_resp.json.return_value = {
        "default_email": f"yandex_{suffix}@oauth.test",
        "first_name": "OAuth",
        "last_name": "User",
    }

    def post_side_effect(url, **kwargs):
        return token_resp if "oauth.yandex.ru/token" in str(url) else MagicMock(status_code=500)

    def get_side_effect(url, **kwargs):
        return info_resp if "login.yandex.ru/info" in str(url) else MagicMock(status_code=500)

    return (
        patch("apps.users.api.views.httpx.post", side_effect=post_side_effect),
        patch("apps.users.api.views.httpx.get", side_effect=get_side_effect),
    )


def _vk_httpx_mock(suffix: str):
    auth_resp = MagicMock(status_code=200)
    auth_resp.json.return_value = {"access_token": "vk-access"}
    user_resp = MagicMock(status_code=200)
    user_resp.json.return_value = {
        "user": {
            "email": f"vk_{suffix}@oauth.test",
            "first_name": "Vk",
            "last_name": "User",
            "sex": 2,
        }
    }

    def post_side_effect(url, **kwargs):
        u = str(url)
        if "id.vk.com/oauth2/auth" in u:
            return auth_resp
        if "id.vk.ru/oauth2/user_info" in u:
            return user_resp
        return MagicMock(status_code=500)

    return patch("apps.users.api.views.httpx.post", side_effect=post_side_effect)


@override_settings(**_OAUTH_SETTINGS)
class UsersOAuthCallbackHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_yandex_oauth_callback_redirect_status_and_state_handling(self):
        with self.subTest("code_flow_primes_cache"):
            r = self.client.get(
                reverse("users:yandex-callback"),
                {"code": "c", "state": "st-y"},
            )
            self.assertEqual(r.status_code, status.HTTP_302_FOUND)
            self.assertTrue(r.url.startswith("http://frontend.test/yandex"))
            self.assertIn("provider=yandex", r.url)
            self.assertIsNotNone(cache.get("oauth:yandex:state:st-y"))
        with self.subTest("provider_error_in_redirect"):
            r = self.client.get(
                reverse("users:yandex-callback"),
                {"error": "access_denied", "state": "s"},
            )
            self.assertEqual(r.status_code, status.HTTP_302_FOUND)
            self.assertIn("error=access_denied", r.url)
        with self.subTest("missing_code_yields_invalid_payload"):
            r = self.client.get(reverse("users:yandex-callback"))
            self.assertEqual(r.status_code, status.HTTP_302_FOUND)
            self.assertIn("invalid_callback_payload", r.url)

    def test_vk_oauth_callback_redirect_status_and_state_handling(self):
        with self.subTest("code_flow_primes_cache"):
            r = self.client.get(
                reverse("users:vk-callback"),
                {"code": "vk", "state": "st-v", "device_id": "d1"},
            )
            self.assertEqual(r.status_code, status.HTTP_302_FOUND)
            self.assertTrue(r.url.startswith("http://frontend.test/vk"))
            self.assertIsNotNone(cache.get("oauth:vk:state:st-v"))
        with self.subTest("missing_code_yields_invalid_payload"):
            r = self.client.get(reverse("users:vk-callback"))
            self.assertEqual(r.status_code, status.HTTP_302_FOUND)
            self.assertIn("invalid_callback_payload", r.url)


@override_settings(**_OAUTH_SETTINGS)
class UsersOAuthExchangeHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_yandex_exchange_rejects_missing_cache_state_with_400(self):
        r = self.client.post(
            reverse("users:yandex-exchange"),
            {"code": "any", "state": "ghost"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["error"], "invalid_state")

    def test_yandex_exchange_with_valid_state_and_stub_http_returns_200_and_user(self):
        suf = uuid.uuid4().hex[:10]
        cache.set("oauth:yandex:state:ok-y", 1, timeout=600)
        p_post, p_get = _yandex_httpx_mocks(suf)
        with p_post, p_get:
            r = self.client.post(
                reverse("users:yandex-exchange"),
                {"code": "code", "state": "ok-y"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", r.data)
        self.assertTrue(
            User.objects.filter(
                email_cipher=encrypt_data(f"yandex_{suf}@oauth.test"),
            ).exists()
        )

    def test_vk_exchange_requires_all_fields_returns_400_on_empty_body(self):
        r = self.client.post(reverse("users:vk-exchange"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["error"], "invalid_request")

    def test_vk_exchange_rejects_state_not_in_cache_returns_400(self):
        r = self.client.post(
            reverse("users:vk-exchange"),
            {
                "code": "c",
                "state": "missing",
                "code_verifier": "cv",
                "device_id": "d",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data["error"], "invalid_state")

    def test_vk_exchange_success_returns_200_and_creates_user(self):
        suf = uuid.uuid4().hex[:10]
        cache.set("oauth:vk:state:ok-v", 1, timeout=600)
        with _vk_httpx_mock(suf):
            r = self.client.post(
                reverse("users:vk-exchange"),
                {
                    "code": "auth",
                    "state": "ok-v",
                    "code_verifier": "verifier",
                    "device_id": "device",
                },
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", r.data)
        self.assertTrue(
            User.objects.filter(email_cipher=encrypt_data(f"vk_{suf}@oauth.test")).exists()
        )
