import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.users.api.views import (
    LoginView,
    ProfileView,
    RecoverPasswordView,
    RefreshTokenView,
    RegisterView,
    ResetPasswordView,
)


class UsersApiUnitTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        os.environ["FRONTEND_HOST"] = "http://localhost:5173"

    def test_register_success(self):
        request = self.factory.post(
            "/api/auth/register/",
            {"email": "student@example.com", "pass_hash": "StrongPass123!"},
            format="json",
        )
        view = RegisterView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            "email_cipher": "enc_email",
            "phone_cipher": None,
            "pass_hash": "StrongPass123!",
        }
        mock_user = MagicMock()
        tokens = {"access_token": "a", "refresh_token": "r"}

        with patch("apps.users.api.views.RegisterSerializer", return_value=serializer), patch(
            "apps.users.api.views.User.objects.create_user", return_value=mock_user
        ) as create_user_mock, patch(
            "apps.users.api.views.get_tokens_for_user", return_value=tokens
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)
        create_user_mock.assert_called_once_with(
            email_cipher="enc_email", phone_cipher=None, password="StrongPass123!"
        )

    def test_register_invalid_payload(self):
        request = self.factory.post("/api/auth/register/", {}, format="json")
        view = RegisterView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"non_field_errors": [
            "Необходимо указать email или phone_number"]}

        with patch("apps.users.api.views.RegisterSerializer", return_value=serializer):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("non_field_errors", response.data)

    def test_login_success(self):
        request = self.factory.post(
            "/api/auth/login/",
            {"email": "student@example.com", "pass_hash": "StrongPass123!"},
            format="json",
        )
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"user": MagicMock()}
        tokens = {"access_token": "a", "refresh_token": "r"}

        with patch("apps.users.api.views.LoginSerializer", return_value=serializer), patch(
            "apps.users.api.views.get_tokens_for_user", return_value=tokens
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)

    def test_refresh_requires_token(self):
        request = self.factory.post("/api/auth/token/refresh/", {}, format="json")
        response = RefreshTokenView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "refresh_token обязателен")

    def test_refresh_invalid_token(self):
        request = self.factory.post(
            "/api/auth/token/refresh/",
            {"refresh_token": "bad_token"},
            format="json",
        )

        with patch("apps.users.api.views.RefreshToken", side_effect=Exception("bad")):
            response = RefreshTokenView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Невалидный или истекший refresh_token")

    def test_reset_requires_email_or_phone(self):
        request = self.factory.post("/api/auth/reset/", {}, format="json")
        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"],
                         "Необходимо указать email или phone_number")

    def test_reset_user_not_found(self):
        request = self.factory.post(
            "/api/auth/reset/",
            {"email": "missing@example.com"},
            format="json",
        )

        with patch("apps.users.api.views.User.objects.filter") as filter_mock:
            filter_mock.return_value.first.return_value = None
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Пользователь не найден")

    def test_reset_success(self):
        request = self.factory.post(
            "/api/auth/reset/",
            {"email": "student@example.com"},
            format="json",
        )
        mock_user = MagicMock()

        with patch("apps.users.api.views.User.objects.filter") as filter_mock, patch(
            "apps.users.api.views.set_reset_token", return_value="reset-token"
        ), patch("apps.users.api.views.send_mail", return_value=1) as send_mail_mock:
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        send_mail_mock.assert_called_once()

    def test_recover_requires_token_and_password(self):
        request = self.factory.patch("/api/auth/recover/set/", {}, format="json")
        response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "token и password обязательны")

    def test_recover_invalid_token(self):
        request = self.factory.patch(
            "/api/auth/recover/set/",
            {"token": "invalid", "password_hash": "NewStrongPass123!"},
            format="json",
        )

        with patch("apps.users.api.views.User.objects.filter") as filter_mock:
            filter_mock.return_value.first.return_value = None
            response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Невалидный или истёкший токен")

    def test_recover_success(self):
        request = self.factory.patch(
            "/api/auth/recover/set/",
            {"token": "valid-token", "password_hash": "NewStrongPass123!"},
            format="json",
        )

        mock_user = MagicMock()
        tokens = {"access_token": "a", "refresh_token": "r"}

        with patch("apps.users.api.views.User.objects.filter") as filter_mock, patch(
            "apps.users.api.views.get_tokens_for_user", return_value=tokens
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_user.set_password.assert_called_once_with("NewStrongPass123!")
        self.assertIsNone(mock_user.reset_token)
        self.assertIsNone(mock_user.reset_token_expires)

    def test_profile_requires_auth(self):
        request = self.factory.get("/api/app/profile/")
        response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_success(self):
        request = self.factory.get("/api/app/profile/")
        auth_user = SimpleNamespace(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        wrapper_serializer = MagicMock()
        wrapper_serializer.data = {"email": "student@example.com"}
        mock_profile = MagicMock()

        with patch(
            "apps.users.api.views.Profile.objects.get_or_create",
            return_value=(mock_profile, True),
        ), patch(
            "apps.users.api.views.UserProfileSerializer", return_value=wrapper_serializer
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "student@example.com")

    def test_profile_patch_validation_error(self):
        request = self.factory.patch(
            "/api/app/profile/", {"gender": "X"}, format="json")
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"gender": ["Допустимые значения: Мужской, Женский"]}

        with patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gender", response.data)

    def test_profile_patch_success(self):
        request = self.factory.patch(
            "/api/app/profile/",
            {
                "first_name": "Иван",
                "last_name": "Петров",
                "email": "new.student@example.com",
                "phone_number": "+79990001122",
                "gender": "Мужской",
            },
            format="json",
        )
        auth_user = MagicMock(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {
            "first_name": "Иван",
            "last_name": "Петров",
            "email_cipher": "enc_email",
            "phone_cipher": "enc_phone",
            "gender": "Мужской",
        }
        mock_profile = MagicMock()

        with patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer), patch(
            "apps.users.api.views.Profile.objects.get_or_create",
            return_value=(mock_profile, True),
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        auth_user.save.assert_called_once()
        mock_profile.save.assert_called_once()
