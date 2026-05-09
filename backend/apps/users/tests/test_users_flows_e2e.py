import os
import uuid
from unittest.mock import patch

import jwt
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.api.utils.crypto_utils import encrypt_data
from apps.users.api.utils.token_utils import get_tokens_for_user
from apps.users.api.utils.verification_utils import get_verification_code_for_user
from apps.users.models import User


def register_email_and_issue_tokens(client: APIClient, email: str, password: str) -> dict:
    with (
        patch("apps.users.api.views.send_verification_email"),
        patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
    ):
        reg = client.post(
            reverse("users:register"),
            {"email": email, "password": password},
            format="json",
        )
    assert reg.status_code == status.HTTP_200_OK, reg.data
    payload = cache.get(f"pending_registration_email_{encrypt_data(email)}")
    assert payload is not None
    verify = client.post(
        reverse("users:register-verify"),
        {"email": email, "code": payload["code"]},
        format="json",
    )
    assert verify.status_code == status.HTTP_200_OK, verify.data
    return verify.data


class UsersAuthLifecycleHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.uid = uuid.uuid4().hex[:10]

    def test_email_register_verify_login_profile_patch_refresh_login_succeeds(self):
        email = f"lifecycle_{self.uid}@test.com"
        password = "StrongPass123!"
        tokens = register_email_and_issue_tokens(self.client, email, password)
        self.assertEqual(tokens["role"], "student")
        decoded = jwt.decode(tokens["access_token"], options={"verify_signature": False})
        self.assertEqual(decoded["role"], "student")

        login_url = reverse("users:login")
        login_ok = self.client.post(
            login_url,
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(login_ok.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_ok.data['access_token']}")
        profile_url = reverse("users:profile")
        self.assertEqual(self.client.get(profile_url).status_code, status.HTTP_200_OK)
        patch_ok = self.client.patch(
            profile_url,
            {"first_name": "Иван", "last_name": "Тестов"},
            format="json",
        )
        self.assertEqual(patch_ok.status_code, status.HTTP_200_OK)

        user = User.objects.get(email_cipher=encrypt_data(email))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Иван")
        self.assertEqual(user.last_name, "Тестов")

        refresh_ok = self.client.post(
            reverse("users:token-refresh"),
            {"refresh_token": login_ok.data["refresh_token"]},
            format="json",
        )
        self.assertEqual(refresh_ok.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", refresh_ok.data)

        self.client.credentials()
        login_again = self.client.post(
            login_url,
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(login_again.status_code, status.HTTP_200_OK)


class UsersPhoneRegisterHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.phone = f"+7926{uuid.uuid4().int % 10 ** 7:07d}"

    def test_phone_register_then_verify_creates_user_returns_200(self):
        password = "StrongPass123!"
        with (
            patch("apps.users.api.views.send_verification_sms"),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
        ):
            reg = self.client.post(
                reverse("users:register"),
                {"phone_number": self.phone, "password": password},
                format="json",
            )
        self.assertEqual(reg.status_code, status.HTTP_200_OK, reg.data)
        payload = cache.get(f"pending_registration_phone_{encrypt_data(self.phone)}")
        self.assertIsNotNone(payload)
        verify = self.client.post(
            reverse("users:register-verify"),
            {"phone_number": self.phone, "code": payload["code"]},
            format="json",
        )
        self.assertEqual(verify.status_code, status.HTTP_200_OK, verify.data)
        self.assertTrue(User.objects.filter(phone_cipher=encrypt_data(self.phone)).exists())


class UsersEmailChangeHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        base = f"base_{uuid.uuid4().hex[:8]}@test.com"
        self.user = User.objects.create_user(
            email_cipher=encrypt_data(base),
            password="OldPass123!",
        )
        tok = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok['access_token']}")

    def test_profile_patch_new_email_then_verify_updates_cipher_returns_200(self):
        new_email = f"verified_{uuid.uuid4().hex[:8]}@test.com"
        with patch("apps.users.api.views.send_verification_email"):
            pr = self.client.patch(
                reverse("users:profile"),
                {"email": new_email},
                format="json",
            )
        self.assertEqual(pr.status_code, status.HTTP_200_OK)
        cached = get_verification_code_for_user(self.user.id, "email")
        self.assertIsNotNone(cached)
        vr = self.client.post(
            reverse("users:verify-email"),
            {"code": cached["code"]},
            format="json",
        )
        self.assertEqual(vr.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_cipher, encrypt_data(new_email))


class UsersPasswordResetEmailHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.email = f"reset_mail_{uuid.uuid4().hex[:8]}@test.com"
        self.old_password = "OriginalPass123!"
        User.objects.create_user(
            email_cipher=encrypt_data(self.email),
            password=self.old_password,
        )

    @patch.dict(os.environ, {"FRONTEND_HOST": "http://localhost:3000"})
    @patch("apps.users.api.utils.notification_utils.send_mail", return_value=1)
    def test_reset_email_then_recover_patch_issues_tokens_and_new_password_works(self, _m):
        reset_ok = self.client.post(
            reverse("users:reset"),
            {"email": self.email},
            format="json",
        )
        self.assertEqual(reset_ok.status_code, status.HTTP_200_OK)
        user = User.objects.get(email_cipher=encrypt_data(self.email))
        user.refresh_from_db()
        self.assertTrue(user.reset_token)
        new_pw = "FreshPass456!"
        recover_ok = self.client.patch(
            reverse("users:recover_set"),
            {"token": user.reset_token, "password": new_pw},
            format="json",
        )
        self.assertEqual(recover_ok.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", recover_ok.data)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_pw))
        self.assertEqual(user.reset_token, "")
        login_ok = self.client.post(
            reverse("users:login"),
            {"email": self.email, "password": new_pw},
            format="json",
        )
        self.assertEqual(login_ok.status_code, status.HTTP_200_OK)


class UsersPasswordResetPhoneHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.phone = "+79991234001"
        User.objects.create_user(
            phone_cipher=encrypt_data(self.phone),
            password="PhoneUserPass123!",
        )

    @patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0))
    @patch("apps.users.api.views.send_reset_password_sms", return_value=(True, "ok"))
    def test_reset_sms_code_exchange_then_recover_sets_password_returns_200(self, _sms, _rl):
        self.assertEqual(
            self.client.post(
                reverse("users:reset"),
                {"phone_number": self.phone},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        user = User.objects.get(phone_cipher=encrypt_data(self.phone))
        cached = get_verification_code_for_user(user.id, "reset_phone")
        self.assertIsNotNone(cached)
        token_resp = self.client.post(
            reverse("users:recover-phone"),
            {"phone_number": self.phone, "code": cached["code"]},
            format="json",
        )
        self.assertEqual(token_resp.status_code, status.HTTP_200_OK)
        new_pw = "PhoneReset789!"
        patch_ok = self.client.patch(
            reverse("users:recover_set"),
            {"token": token_resp.data["token"], "password": new_pw},
            format="json",
        )
        self.assertEqual(patch_ok.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_pw))
