import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from ..api.errors import VerificationError
from ..api.utils.crypto_utils import encrypt_data
from ..api.utils.token_utils import get_tokens_for_user, set_reset_token
from ..api.views import (
    LoginView,
    ProfileView,
    RecoverPasswordPhoneView,
    RecoverPasswordView,
    RefreshTokenView,
    RegisterView,
    ResetPasswordView,
    VerifyEmailChangeView,
    VerifyPhoneChangeView,
    VerifyRegisterView,
)
from ..models import Profile, User


class RegisterViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        os.environ["FRONTEND_HOST"] = "http://localhost:3000"

    def test_register_email_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/register/",
            {"email": "student@example.com", "password": "StrongPass123!"},
            format="json",
        )
        view = RegisterView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            "email": "student@example.com",
            "password": "StrongPass123!",
        }

        with (
            patch("apps.users.api.views.EmailRegisterSerializer", return_value=serializer),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
            patch("apps.users.api.views.generate_registration_code", return_value="123456"),
            patch("apps.users.api.views.send_verification_email") as send_mock,
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "code_sent")
        send_mock.assert_called_once_with("student@example.com", "123456")

    def test_register_phone_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/register/",
            {"phone_number": "+79991234567", "password": "StrongPass123!"},
            format="json",
        )
        view = RegisterView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            "phone_number": "+79991234567",
            "password": "StrongPass123!",
        }

        with (
            patch("apps.users.api.views.PhoneRegisterSerializer", return_value=serializer),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
            patch("apps.users.api.views.generate_registration_code", return_value="654321"),
            patch("apps.users.api.views.send_verification_sms") as send_mock,
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "code_sent")
        send_mock.assert_called_once_with("+79991234567", "654321")

    def test_register_invalid_payload(self):
        request = self.factory.post("/api/v1/auth/register/", {}, format="json")
        view = RegisterView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)

    def test_register_with_short_password(self):
        request = self.factory.post(
            "/api/v1/auth/register/",
            {"email": "test@example.com", "password": "short"},
            format="json",
        )
        view = RegisterView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"password": ["Пароль должен содержать минимум 8 символов"]}

        with patch("apps.users.api.views.EmailRegisterSerializer", return_value=serializer):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_rate_limited(self):
        request = self.factory.post(
            "/api/v1/auth/register/",
            {"email": "test@example.com", "password": "StrongPass123!"},
            format="json",
        )
        view = RegisterView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            "email": "test@example.com",
            "password": "StrongPass123!",
        }

        with (
            patch("apps.users.api.views.EmailRegisterSerializer", return_value=serializer),
            patch(
                "apps.users.api.views.check_contact_rate_limit",
                return_value=(False, 45),
            ),
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["retry_after"], 45)


class VerifyRegisterViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_verify_register_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/register/verify/",
            {"phone_number": "+79991234567", "code": "123456"},
            format="json",
        )
        view = VerifyRegisterView.as_view()

        reg_data = {
            "contact": "+79991234567",
            "contact_type": "phone",
            "password_hash": "hashed_pw",
        }
        mock_user = MagicMock()
        tokens = {"access_token": "a", "refresh_token": "r", "role": "student"}

        with (
            patch("apps.users.api.views.verify_registration_code", return_value=reg_data),
            patch("apps.users.api.views.encrypt_data", return_value="enc_phone"),
            patch("apps.users.api.views.User.objects.create_user", return_value=mock_user),
            patch("apps.users.api.views.get_tokens_for_user", return_value=tokens),
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)

    def test_verify_register_invalid_code(self):
        request = self.factory.post(
            "/api/v1/auth/register/verify/",
            {"phone_number": "+79991234567", "code": "000000"},
            format="json",
        )
        view = VerifyRegisterView.as_view()

        with patch(
            "apps.users.api.views.verify_registration_code",
            side_effect=VerificationError("invalid", "Неверный код."),
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "invalid")

    def test_verify_register_invalid_payload(self):
        request = self.factory.post(
            "/api/v1/auth/register/verify/",
            {},
            format="json",
        )
        view = VerifyRegisterView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_login_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/login/",
            {"email": "student@example.com", "password": "StrongPass123!"},
            format="json",
        )
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"user": MagicMock()}
        tokens = {"access_token": "a", "refresh_token": "r", "role": "student"}

        with (
            patch("apps.users.api.views.LoginSerializer", return_value=serializer),
            patch("apps.users.api.views.get_tokens_for_user", return_value=tokens),
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)

    def test_login_with_wrong_password(self):
        request = self.factory.post(
            "/api/v1/auth/login/",
            {"email": "test@example.com", "password": "wrongpassword"},
            format="json",
        )
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"non_field_errors": ["Неверный email или пароль"]}

        with patch("apps.users.api.views.LoginSerializer", return_value=serializer):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_without_contact(self):
        request = self.factory.post(
            "/api/v1/auth/login/",
            {"password": "testpass123"},
            format="json",
        )
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"non_field_errors": ["Необходимо указать почту или номер телефона"]}

        with patch("apps.users.api.views.LoginSerializer", return_value=serializer):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshTokenViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_refresh_requires_token(self):
        request = self.factory.post("/api/v1/auth/token/refresh/", {}, format="json")
        response = RefreshTokenView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "refresh_token обязателен")

    def test_refresh_invalid_token(self):
        request = self.factory.post(
            "/api/v1/auth/token/refresh/",
            {"refresh_token": "bad_token"},
            format="json",
        )

        with patch("apps.users.api.views.RefreshToken", side_effect=Exception("bad")):
            response = RefreshTokenView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Невалидный или истекший refresh_token")


class ResetPasswordViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        os.environ["FRONTEND_HOST"] = "http://localhost:3000"

    def test_reset_requires_email_or_phone(self):
        request = self.factory.post("/api/v1/auth/reset/", {}, format="json")
        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Необходимо указать почту или номер телефона")

    def test_reset_user_not_found(self):
        request = self.factory.post(
            "/api/v1/auth/reset/",
            {"email": "missing@example.com"},
            format="json",
        )

        with patch("apps.users.api.views.User.objects.filter") as filter_mock:
            filter_mock.return_value.first.return_value = None
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Пользователь не найден")

    def test_reset_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/reset/",
            {"email": "student@example.com"},
            format="json",
        )
        mock_user = MagicMock()

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch("apps.users.api.views.set_reset_token", return_value="reset-token"),
            patch(
                "apps.users.api.utils.notification_utils.send_mail", return_value=1
            ) as send_mail_mock,
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        send_mail_mock.assert_called_once()


class RecoverPasswordViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_recover_requires_token_and_password(self):
        request = self.factory.patch("/api/v1/auth/recover/set/", {}, format="json")
        response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "token и password_hash обязательны")

    def test_recover_invalid_token(self):
        request = self.factory.patch(
            "/api/v1/auth/recover/set/",
            {"token": "invalid", "password": "NewStrongPass123!"},
            format="json",
        )

        with patch("apps.users.api.views.User.objects.filter") as filter_mock:
            filter_mock.return_value.first.return_value = None
            response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Невалидный или истёкший токен")

    def test_recover_success_mocked(self):
        request = self.factory.patch(
            "/api/v1/auth/recover/set/",
            {"token": "valid-token", "password": "NewStrongPass123!"},
            format="json",
        )

        mock_user = MagicMock()
        tokens = {"access_token": "a", "refresh_token": "r", "role": "student"}

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch("apps.users.api.views.get_tokens_for_user", return_value=tokens),
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_user.set_password.assert_called_once_with("NewStrongPass123!")
        self.assertEqual(mock_user.reset_token, "")
        self.assertIsNone(mock_user.reset_token_expires)


class ProfileViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_profile_requires_auth(self):
        request = self.factory.get("/api/v1/profile/")
        response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_success_mocked(self):
        """Test successful profile retrieval"""
        request = self.factory.get("/api/v1/profile/")
        auth_user = SimpleNamespace(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        wrapper_serializer = MagicMock()
        wrapper_serializer.data = {"email": "student@example.com", "first_name": "Test"}
        mock_profile = MagicMock()

        with (
            patch(
                "apps.users.api.views.Profile.objects.get_or_create",
                return_value=(mock_profile, True),
            ),
            patch(
                "apps.users.api.views.UserProfileSerializer",
                return_value=wrapper_serializer,
            ),
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "student@example.com")

    def test_profile_patch_validation_error(self):
        request = self.factory.patch("/api/v1/profile/", {"gender": "X"}, format="json")
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"gender": ["Допустимые значения: Мужской, Женский"]}

        with patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gender", response.data)

    def test_profile_patch_success_mocked(self):
        request = self.factory.patch(
            "/api/v1/profile/",
            {"first_name": "Иван", "last_name": "Петров"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            "first_name": "Иван",
            "last_name": "Петров",
        }
        mock_profile = MagicMock()

        with (
            patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer),
            patch(
                "apps.users.api.views.Profile.objects.get_or_create",
                return_value=(mock_profile, True),
            ),
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")


class RegisterViewIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("users:register")
        self.verify_url = reverse("users:register-verify")

    def _register_and_verify(self, email, password):
        with (
            patch("apps.users.api.views.send_verification_email"),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
        ):
            reg_response = self.client.post(
                self.register_url,
                {"email": email, "password": password},
                format="json",
            )
        self.assertEqual(reg_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reg_response.data["status"], "code_sent")

        from django.core.cache import cache

        from ..api.utils.crypto_utils import encrypt_data as enc

        cache_key = f"pending_registration_email_{enc(email)}"
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached, "Registration code not found in cache")
        code = cached["code"]

        verify_response = self.client.post(
            self.verify_url,
            {"email": email, "code": code},
            format="json",
        )
        return verify_response

    def test_register_with_email_creates_user_in_db(self):
        response = self._register_and_verify("newuser@example.com", "testpass123")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("role", response.data)

        self.assertTrue(
            User.objects.filter(email_cipher=encrypt_data("newuser@example.com")).exists()
        )

    def test_newly_registered_user_has_student_role(self):
        response = self._register_and_verify("student@example.com", "testpass123")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "student")

        access_token = response.data["access_token"]
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        self.assertEqual(decoded["role"], "student")

        user = User.objects.get(email_cipher=encrypt_data("student@example.com"))
        self.assertEqual(user.role, User.ROLE_STUDENT)

    def test_register_duplicate_email(self):
        email = "duplicate@example.com"
        User.objects.create_user(email_cipher=encrypt_data(email), password="testpass123")

        with (
            patch("apps.users.api.views.send_verification_email"),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
        ):
            response = self.client.post(
                self.register_url,
                {"email": email, "password": "testpass123"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("email", response.data)


class LoginViewIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("users:login")
        self.email = "test@example.com"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            email_cipher=encrypt_data(self.email), password=self.password
        )

    def test_login_with_email(self):
        data = {"email": self.email, "password": self.password}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("role", response.data)

    def test_login_returns_correct_role(self):
        teacher_email = "teacher@example.com"
        teacher = User.objects.create_user(
            email_cipher=encrypt_data(teacher_email),
            password=self.password,
            role=User.ROLE_TEACHER,
        )

        data = {"email": teacher_email, "password": self.password}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], User.ROLE_TEACHER)

        access_token = response.data["access_token"]
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        self.assertEqual(decoded["role"], User.ROLE_TEACHER)


class RefreshTokenViewIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("users:token-refresh")
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("test@example.com"), password="testpass123"
        )

    def test_refresh_token_success(self):
        tokens = get_tokens_for_user(self.user)

        data = {"refresh_token": tokens["refresh_token"]}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)


class RecoverPasswordViewIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("users:recover_set")
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("test@example.com"), password="oldpass123"
        )
        self.token = set_reset_token(self.user)

    def test_recover_password_success(self):
        new_password = "newpass123"
        data = {"token": self.token, "password": new_password}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        self.assertEqual(self.user.reset_token, "")
        self.assertIsNone(self.user.reset_token_expires)

    def test_recover_password_with_expired_token(self):
        self.user.reset_token_expires = timezone.now() - timedelta(hours=1)
        self.user.save()

        data = {"token": self.token, "password": "newpass123"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RecoverPasswordPhoneViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_recover_phone_invalid_payload(self):
        request = self.factory.post(
            "/api/v1/auth/recover/phone/",
            {},
            format="json",
        )
        response = RecoverPasswordPhoneView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recover_phone_non_digit_code(self):
        request = self.factory.post(
            "/api/v1/auth/recover/phone/",
            {"phone_number": "+79991234567", "code": "abcdef"},
            format="json",
        )
        response = RecoverPasswordPhoneView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recover_phone_user_not_found(self):
        request = self.factory.post(
            "/api/v1/auth/recover/phone/",
            {"phone_number": "+79991234567", "code": "123456"},
            format="json",
        )

        with patch("apps.users.api.views.User.objects.filter") as filter_mock:
            filter_mock.return_value.first.return_value = None
            response = RecoverPasswordPhoneView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Пользователь не найден")

    def test_recover_phone_invalid_code(self):
        request = self.factory.post(
            "/api/v1/auth/recover/phone/",
            {"phone_number": "+79991234567", "code": "000000"},
            format="json",
        )

        mock_user = MagicMock(id=1)

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch(
                "apps.users.api.views.verify_code",
                side_effect=VerificationError("invalid", "Неверный код"),
            ),
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = RecoverPasswordPhoneView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "invalid")

    def test_recover_phone_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/recover/phone/",
            {"phone_number": "+79991234567", "code": "123456"},
            format="json",
        )

        mock_user = MagicMock(id=1)

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch("apps.users.api.views.verify_code", return_value="+79991234567"),
            patch("apps.users.api.views.set_reset_token", return_value="reset-tok") as reset_mock,
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = RecoverPasswordPhoneView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["token"], "reset-tok")
        reset_mock.assert_called_once_with(mock_user)


class VerifyEmailChangeViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_verify_email_requires_auth(self):
        request = self.factory.post(
            "/api/v1/profile/verify_email/",
            {"code": "123456"},
            format="json",
        )
        response = VerifyEmailChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_email_invalid_code_format(self):
        request = self.factory.post(
            "/api/v1/profile/verify_email/",
            {"code": "short"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        response = VerifyEmailChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_verification_error(self):
        request = self.factory.post(
            "/api/v1/profile/verify_email/",
            {"code": "000000"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True, id=1)
        force_authenticate(request, user=auth_user)

        with patch(
            "apps.users.api.views.verify_code",
            side_effect=VerificationError("invalid", "Неверный код"),
        ):
            response = VerifyEmailChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "invalid")

    def test_verify_email_success_mocked(self):
        request = self.factory.post(
            "/api/v1/profile/verify_email/",
            {"code": "123456"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True, id=1, pk=1)
        force_authenticate(request, user=auth_user)

        with (
            patch("apps.users.api.views.verify_code", return_value="new@example.com"),
            patch("apps.users.api.views.encrypt_data", return_value="enc_email"),
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
        ):
            filter_mock.return_value.exclude.return_value.exists.return_value = False
            response = VerifyEmailChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(auth_user.email_cipher, "enc_email")
        auth_user.save.assert_called_once_with(update_fields=["email_cipher"])

    def test_verify_email_duplicate_blocked(self):
        request = self.factory.post(
            "/api/v1/profile/verify_email/",
            {"code": "123456"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True, id=1, pk=1)
        force_authenticate(request, user=auth_user)

        with (
            patch("apps.users.api.views.verify_code", return_value="taken@example.com"),
            patch("apps.users.api.views.encrypt_data", return_value="enc_taken"),
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
        ):
            filter_mock.return_value.exclude.return_value.exists.return_value = True
            response = VerifyEmailChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)


class VerifyPhoneChangeViewUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_verify_phone_requires_auth(self):
        request = self.factory.post(
            "/api/v1/profile/verify_phone/",
            {"code": "123456"},
            format="json",
        )
        response = VerifyPhoneChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_phone_verification_error(self):
        request = self.factory.post(
            "/api/v1/profile/verify_phone/",
            {"code": "000000"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True, id=1)
        force_authenticate(request, user=auth_user)

        with patch(
            "apps.users.api.views.verify_code",
            side_effect=VerificationError("expired", "Код истек. Действителен 5 минут"),
        ):
            response = VerifyPhoneChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "expired")

    def test_verify_phone_success_mocked(self):
        request = self.factory.post(
            "/api/v1/profile/verify_phone/",
            {"code": "123456"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True, id=1, pk=1)
        force_authenticate(request, user=auth_user)

        with (
            patch("apps.users.api.views.verify_code", return_value="+79990001122"),
            patch("apps.users.api.views.encrypt_data", return_value="enc_phone"),
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
        ):
            filter_mock.return_value.exclude.return_value.exists.return_value = False
            response = VerifyPhoneChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(auth_user.phone_cipher, "enc_phone")
        auth_user.save.assert_called_once_with(update_fields=["phone_cipher"])

    def test_verify_phone_duplicate_blocked(self):
        request = self.factory.post(
            "/api/v1/profile/verify_phone/",
            {"code": "123456"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True, id=1, pk=1)
        force_authenticate(request, user=auth_user)

        with (
            patch("apps.users.api.views.verify_code", return_value="+79990001122"),
            patch("apps.users.api.views.encrypt_data", return_value="enc_taken"),
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
        ):
            filter_mock.return_value.exclude.return_value.exists.return_value = True
            response = VerifyPhoneChangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)


class LoginViewLockoutUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_login_lockout_after_max_attempts(self):
        """After MAX_LOGIN_ATTEMPTS failed logins the account is locked out."""
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"non_field_errors": ["Неверные учетные данные"]}

        with (
            patch("apps.users.api.views.LoginSerializer", return_value=serializer),
            patch("apps.users.api.views.cache") as mock_cache,
        ):
            mock_cache.get.return_value = None  # no lockout, no prior attempts

            for attempt in range(1, 6):
                mock_cache.get.side_effect = [
                    None,  # lockout_key check
                    attempt - 1,  # attempts_key check
                ]
                request = self.factory.post(
                    "/api/v1/auth/login/",
                    {"email": "user@example.com", "password": "wrong"},
                    format="json",
                )
                response = view(request)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            # 5th attempt triggers lockout — cache.set(lockout_key, ...) should have been called
            lockout_calls = [c for c in mock_cache.set.call_args_list if "login_lockout_" in str(c)]
            self.assertTrue(len(lockout_calls) > 0, "Lockout key was never set")

    def test_login_returns_429_when_locked(self):
        request = self.factory.post(
            "/api/v1/auth/login/",
            {"email": "user@example.com", "password": "wrong"},
            format="json",
        )

        with patch("apps.users.api.views.cache") as mock_cache:
            mock_cache.get.return_value = True  # lockout_key exists

            response = LoginView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("retry_after", response.data)


class ResetPasswordViewPhoneUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_reset_phone_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/reset/",
            {"phone_number": "+79991234567"},
            format="json",
        )

        mock_user = MagicMock(id=1)

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
            patch(
                "apps.users.api.views.generate_verification_code_for_user",
                return_value="654321",
            ),
            patch(
                "apps.users.api.views.send_reset_password_sms",
                return_value=(True, "ok"),
            ) as sms_mock,
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        sms_mock.assert_called_once_with("+79991234567", "654321")

    def test_reset_phone_rate_limited(self):
        request = self.factory.post(
            "/api/v1/auth/reset/",
            {"phone_number": "+79991234567"},
            format="json",
        )

        mock_user = MagicMock(id=1)

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch(
                "apps.users.api.views.check_contact_rate_limit",
                return_value=(False, 42),
            ),
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["retry_after"], 42)

    def test_reset_phone_sms_failure(self):
        request = self.factory.post(
            "/api/v1/auth/reset/",
            {"phone_number": "+79991234567"},
            format="json",
        )

        mock_user = MagicMock(id=1)

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
            patch(
                "apps.users.api.views.generate_verification_code_for_user",
                return_value="111111",
            ),
            patch(
                "apps.users.api.views.send_reset_password_sms",
                return_value=(False, "fail"),
            ),
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_reset_email_send_failure(self):
        os.environ["FRONTEND_HOST"] = "http://localhost:3000"
        request = self.factory.post(
            "/api/v1/auth/reset/",
            {"email": "user@example.com"},
            format="json",
        )

        mock_user = MagicMock(id=1)

        with (
            patch("apps.users.api.views.User.objects.filter") as filter_mock,
            patch("apps.users.api.views.set_reset_token", return_value="tok"),
            patch(
                "apps.users.api.views.send_reset_password_email",
                return_value=(False, "error"),
            ),
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileEmailPhoneChangeUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_profile_patch_email_triggers_verification(self):
        request = self.factory.patch(
            "/api/v1/profile/",
            {"email": "new@example.com"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"email": "new@example.com"}
        mock_profile = MagicMock()

        with (
            patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer),
            patch(
                "apps.users.api.views.Profile.objects.get_or_create",
                return_value=(mock_profile, True),
            ),
            patch(
                "apps.users.api.views.generate_verification_code_for_user",
                return_value="111111",
            ) as gen_mock,
            patch("apps.users.api.views.send_verification_email") as send_mock,
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gen_mock.assert_called_once_with(
            user_id=auth_user.id,
            contact_type="email",
            new_contact="new@example.com",
        )
        send_mock.assert_called_once_with("new@example.com", "111111")

    def test_profile_patch_phone_triggers_verification(self):
        request = self.factory.patch(
            "/api/v1/profile/",
            {"phone_number": "+79990001122"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"phone_number": "+79990001122"}
        mock_profile = MagicMock()

        with (
            patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer),
            patch(
                "apps.users.api.views.Profile.objects.get_or_create",
                return_value=(mock_profile, True),
            ),
            patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)),
            patch(
                "apps.users.api.views.generate_verification_code_for_user",
                return_value="222222",
            ) as gen_mock,
            patch("apps.users.api.views.send_verification_sms") as send_mock,
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gen_mock.assert_called_once_with(
            user_id=auth_user.id,
            contact_type="phone",
            new_contact="+79990001122",
        )
        send_mock.assert_called_once_with("+79990001122", "222222")

    def test_profile_patch_phone_rate_limited(self):
        request = self.factory.patch(
            "/api/v1/profile/",
            {"phone_number": "+79990001122"},
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"phone_number": "+79990001122"}
        mock_profile = MagicMock()

        with (
            patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer),
            patch(
                "apps.users.api.views.Profile.objects.get_or_create",
                return_value=(mock_profile, True),
            ),
            patch(
                "apps.users.api.views.check_contact_rate_limit",
                return_value=(False, 30),
            ),
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["retry_after"], 30)


class VerifyRegisterViewEmailUnitTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_verify_register_email_success_mocked(self):
        request = self.factory.post(
            "/api/v1/auth/register/verify/",
            {"email": "new@example.com", "code": "123456"},
            format="json",
        )
        view = VerifyRegisterView.as_view()

        reg_data = {
            "contact": "new@example.com",
            "contact_type": "email",
            "password_hash": "hashed_pw",
        }
        mock_user = MagicMock()
        tokens = {"access_token": "a", "refresh_token": "r", "role": "student"}

        with (
            patch("apps.users.api.views.verify_registration_code", return_value=reg_data),
            patch("apps.users.api.views.encrypt_data", return_value="enc_email"),
            patch("apps.users.api.views.User.objects.create_user", return_value=mock_user),
            patch("apps.users.api.views.get_tokens_for_user", return_value=tokens),
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)

    def test_verify_register_expired_code(self):
        request = self.factory.post(
            "/api/v1/auth/register/verify/",
            {"email": "new@example.com", "code": "123456"},
            format="json",
        )
        view = VerifyRegisterView.as_view()

        with patch(
            "apps.users.api.views.verify_registration_code",
            side_effect=VerificationError("expired", "Код истек. Действителен 5 минут"),
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "expired")


class ProfileViewIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("users:profile")
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("test@example.com"),
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def test_get_profile_authenticated(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("email", response.data)
        self.assertIn("first_name", response.data)
        self.assertIn("last_name", response.data)

    def test_update_profile_first_name(self):
        data = {"first_name": "Updated"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")

    def test_update_profile_gender(self):
        data = {"gender": "М"}
        response = self.client.patch(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.gender, "М")

    def test_profile_auto_created(self):
        Profile.objects.filter(user=self.user).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
