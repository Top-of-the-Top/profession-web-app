import os
import uuid
from datetime import timedelta
from unittest.mock import patch

import jwt
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.api.utils.crypto_utils import encrypt_data
from apps.users.api.utils.token_utils import get_tokens_for_user, set_reset_token
from apps.users.models import Profile, User


class UsersRegisterValidationHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_register_without_contact_returns_403(self):
        r = self.client.post(reverse("users:register"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", r.data)

    def test_register_short_password_returns_403(self):
        r = self.client.post(
            reverse("users:register"),
            {"email": "short_pw@test.com", "password": "short"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("details", r.data)

    def test_register_duplicate_email_returns_403(self):
        email = "dup@test.com"
        User.objects.create_user(email_cipher=encrypt_data(email), password="Pass12345!")
        with (
            patch("apps.users.api.views.send_verification_email"),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
        ):
            r = self.client.post(
                reverse("users:register"),
                {"email": email, "password": "Pass12345!"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("details", r.data)

    def test_register_when_rate_limited_returns_429(self):
        with (
            patch("apps.users.api.views.EmailRegisterSerializer") as ser_cls,
            patch(
                "apps.users.api.views.check_contact_rate_limit",
                return_value=(False, 44),
            ),
        ):
            mock_ser = ser_cls.return_value
            mock_ser.is_valid.return_value = True
            mock_ser.validated_data = {"email": "rl@test.com", "password": "Pass12345!"}
            r = self.client.post(
                reverse("users:register"),
                {"email": "rl@test.com", "password": "Pass12345!"},
                format="json",
            )
        self.assertEqual(r.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(r.data["details"]["retry_after"], 44)


class UsersVerifyRegisterValidationHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_verify_register_empty_payload_returns_400(self):
        r = self.client.post(reverse("users:register-verify"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_register_wrong_code_returns_400(self):
        email = f"verify_bad_{uuid.uuid4().hex[:8]}@test.com"
        pwd = "Pass12345!"
        with (
            patch("apps.users.api.views.send_verification_email"),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
        ):
            self.client.post(
                reverse("users:register"),
                {"email": email, "password": pwd},
                format="json",
            )
        r = self.client.post(
            reverse("users:register-verify"),
            {"email": email, "code": "000000"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", r.data)


class UsersLoginHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.email = "login@test.com"
        self.password = "Pass12345!"
        User.objects.create_user(
            email_cipher=encrypt_data(self.email),
            password=self.password,
        )

    def test_login_valid_credentials_returns_200_with_tokens(self):
        r = self.client.post(
            reverse("users:login"),
            {"email": self.email, "password": self.password},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", r.data)
        self.assertIn("refresh_token", r.data)
        self.assertEqual(r.data["role"], User.ROLE_STUDENT)

    def test_login_teacher_role_in_response_and_jwt_claim(self):
        teacher_mail = "teacher_role@test.com"
        User.objects.create_user(
            email_cipher=encrypt_data(teacher_mail),
            password=self.password,
            role=User.ROLE_TEACHER,
        )
        r = self.client.post(
            reverse("users:login"),
            {"email": teacher_mail, "password": self.password},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["role"], User.ROLE_TEACHER)
        decoded = jwt.decode(r.data["access_token"], options={"verify_signature": False})
        self.assertEqual(decoded["role"], User.ROLE_TEACHER)

    def test_login_invalid_password_returns_400(self):
        r = self.client.post(
            reverse("users:login"),
            {"email": self.email, "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_fifth_failure_still_400_sixth_returns_429_lockout(self):
        url = reverse("users:login")
        for _ in range(5):
            r = self.client.post(
                url,
                {"email": self.email, "password": "bad"},
                format="json",
            )
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        locked = self.client.post(
            url,
            {"email": self.email, "password": "bad"},
            format="json",
        )
        self.assertEqual(locked.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("retry_after", locked.data["details"])


class UsersRefreshTokenHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("refresh@test.com"),
            password="Pass12345!",
        )

    def test_refresh_without_token_returns_401(self):
        r = self.client.post(reverse("users:token-refresh"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_invalid_token_returns_401(self):
        r = self.client.post(
            reverse("users:token-refresh"),
            {"refresh_token": "invalid"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class UsersResetPasswordHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_reset_without_contact_returns_403(self):
        r = self.client.post(reverse("users:reset"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_unknown_email_returns_403(self):
        r = self.client.post(
            reverse("users:reset"),
            {"email": "nobody@test.com"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    @patch.dict(os.environ, {"FRONTEND_HOST": "http://localhost:3000"})
    @patch("apps.users.api.views.send_reset_password_email", return_value=(False, "fail"))
    def test_reset_known_user_mail_send_failure_returns_500(self, _send):
        User.objects.create_user(
            email_cipher=encrypt_data("exists@test.com"),
            password="Pass12345!",
        )
        r = self.client.post(
            reverse("users:reset"),
            {"email": "exists@test.com"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class UsersRecoverPasswordHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_recover_without_token_or_password_returns_403(self):
        r = self.client.patch(reverse("users:recover_set"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_recover_expired_token_returns_403(self):
        user = User.objects.create_user(
            email_cipher=encrypt_data("exp@test.com"),
            password="Pass12345!",
        )
        tok = set_reset_token(user)
        user.refresh_from_db()
        user.reset_token_expires = timezone.now() - timedelta(hours=1)
        user.save(update_fields=["reset_token_expires"])
        r = self.client.patch(
            reverse("users:recover_set"),
            {"token": tok, "password": "NewPass123!"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class UsersRecoverPasswordPhoneValidationHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_recover_phone_empty_body_returns_400(self):
        r = self.client.post(reverse("users:recover-phone"), {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recover_phone_non_digit_code_returns_400(self):
        r = self.client.post(
            reverse("users:recover-phone"),
            {"phone_number": "+79991234567", "code": "abcdef"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recover_phone_unknown_user_returns_403(self):
        r = self.client.post(
            reverse("users:recover-phone"),
            {"phone_number": "+79990001122", "code": "123456"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class UsersProfileHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("prof@test.com"),
            password="Pass12345!",
            first_name="A",
            last_name="B",
        )
        tok = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tok['access_token']}")

    def test_profile_get_without_auth_returns_401(self):
        self.client.credentials()
        r = self.client.get(reverse("users:profile"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_authenticated_returns_200_with_identity_fields(self):
        r = self.client.get(reverse("users:profile"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("email", r.data)
        self.assertIn("first_name", r.data)

    def test_profile_patch_invalid_gender_returns_400(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {get_tokens_for_user(self.user)['access_token']}"
        )
        r = self.client.patch(
            reverse("users:profile"),
            {"gender": "invalid"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_get_creates_missing_profile_returns_200(self):
        Profile.objects.filter(user=self.user).delete()
        r = self.client.get(reverse("users:profile"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())


class UsersVerifyContactChangeAuthHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()

    def test_verify_email_without_auth_returns_401(self):
        r = self.client.post(
            reverse("users:verify-email"),
            {"code": "123456"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_phone_without_auth_returns_401(self):
        r = self.client.post(
            reverse("users:verify-phone"),
            {"code": "123456"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
