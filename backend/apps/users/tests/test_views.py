import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from datetime import timedelta

from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework import status
from ..api.utils import get_tokens_for_user
import jwt

from ..models import User, Profile
from ..api.utils import encrypt_data, decrypt_data, set_reset_token
from ..api.views import (
    LoginView,
    ProfileView,
    RecoverPasswordView,
    RecoverPasswordPhoneView,
    RefreshTokenView,
    RegisterView,
    ResetPasswordView,
    VerifyRegisterView,
    VerifyEmailChangeView,
    VerifyPhoneChangeView,
)
from ..api.errors import VerificationError

class RegisterViewUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        os.environ["FRONTEND_HOST"] = "http://localhost:5173"

    def test_register_email_success_mocked(self):
        request = self.factory.post(
            "/api/auth/register/",
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

        with patch("apps.users.api.views.EmailRegisterSerializer", return_value=serializer), \
             patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)), \
             patch("apps.users.api.views.generate_registration_code", return_value="123456"), \
             patch("apps.users.api.views.send_verification_email") as send_mock:
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "code_sent")
        send_mock.assert_called_once_with("student@example.com", "123456")

    def test_register_phone_success_mocked(self):
        request = self.factory.post(
            "/api/auth/register/",
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

        with patch("apps.users.api.views.PhoneRegisterSerializer", return_value=serializer), \
             patch("apps.users.api.views.check_contact_rate_limit", return_value=(True, 0)), \
             patch("apps.users.api.views.generate_registration_code", return_value="654321"), \
             patch("apps.users.api.views.send_verification_sms") as send_mock:
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "code_sent")
        send_mock.assert_called_once_with("+79991234567", "654321")

    def test_register_invalid_payload(self):
        request = self.factory.post("/api/auth/register/", {}, format="json")
        view = RegisterView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)

    def test_register_with_short_password(self):
        request = self.factory.post(
            "/api/auth/register/",
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
            "/api/auth/register/",
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

        with patch("apps.users.api.views.EmailRegisterSerializer", return_value=serializer), \
             patch("apps.users.api.views.check_contact_rate_limit", return_value=(False, 45)):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["retry_after"], 45)


class VerifyRegisterViewUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def test_verify_register_success_mocked(self):
        request = self.factory.post(
            "/api/auth/register/verify/",
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

        with patch("apps.users.api.views.verify_registration_code", return_value=reg_data), \
             patch("apps.users.api.views.encrypt_data", return_value="enc_phone"), \
             patch("apps.users.api.views.User.objects.create_user", return_value=mock_user), \
             patch("apps.users.api.views.get_tokens_for_user", return_value=tokens):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)

    def test_verify_register_invalid_code(self):
        request = self.factory.post(
            "/api/auth/register/verify/",
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
            "/api/auth/register/verify/",
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
            "/api/auth/login/",
            {"email": "student@example.com", "password": "StrongPass123!"},
            format="json",
        )
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = True
        serializer.validated_data = {"user": MagicMock()}
        tokens = {"access_token": "a", "refresh_token": "r", "role": "student"}

        with patch("apps.users.api.views.LoginSerializer", return_value=serializer), patch(
            "apps.users.api.views.get_tokens_for_user", return_value=tokens
        ):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, tokens)

    def test_login_with_wrong_password(self):
        request = self.factory.post(
            "/api/auth/login/",
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
            "/api/auth/login/",
            {"password": "testpass123"},
            format="json",
        )
        view = LoginView.as_view()

        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = {"non_field_errors": ["Необходимо указать email или phone_number"]}

        with patch("apps.users.api.views.LoginSerializer", return_value=serializer):
            response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshTokenViewUnitTest(SimpleTestCase):


    def setUp(self):
        self.factory = APIRequestFactory()

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
        self.assertEqual(response.data["detail"], "Невалидный или истекший refresh_token")


class ResetPasswordViewUnitTest(SimpleTestCase):


    def setUp(self):
        self.factory = APIRequestFactory()
        os.environ["FRONTEND_HOST"] = "http://localhost:5173"

    def test_reset_requires_email_or_phone(self):
        request = self.factory.post("/api/auth/reset/", {}, format="json")
        response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Необходимо указать email или phone_number")

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

    def test_reset_success_mocked(self):
        request = self.factory.post(
            "/api/auth/reset/",
            {"email": "student@example.com"},
            format="json",
        )
        mock_user = MagicMock()

        with patch("apps.users.api.views.User.objects.filter") as filter_mock, patch(
            "apps.users.api.views.set_reset_token", return_value="reset-token"
        ), patch('apps.users.api.utils.send_mail', return_value=1) as send_mail_mock:
            filter_mock.return_value.first.return_value = mock_user
            response = ResetPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        send_mail_mock.assert_called_once()


class RecoverPasswordViewUnitTest(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

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

    def test_recover_success_mocked(self):
        request = self.factory.patch(
            "/api/auth/recover/set/",
            {"token": "valid-token", "password_hash": "NewStrongPass123!"},
            format="json",
        )

        mock_user = MagicMock()
        tokens = {"access_token": "a", "refresh_token": "r", "role": "student"}

        with patch("apps.users.api.views.User.objects.filter") as filter_mock, patch(
            "apps.users.api.views.get_tokens_for_user", return_value=tokens
        ):
            filter_mock.return_value.first.return_value = mock_user
            response = RecoverPasswordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_user.set_password.assert_called_once_with("NewStrongPass123!")
        self.assertIsNone(mock_user.reset_token)
        self.assertIsNone(mock_user.reset_token_expires)


class ProfileViewUnitTest(SimpleTestCase):


    def setUp(self):
        self.factory = APIRequestFactory()

    def test_profile_requires_auth(self):
        request = self.factory.get("/api/app/profile/")
        response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_success_mocked(self):
        """Test successful profile retrieval"""
        request = self.factory.get("/api/app/profile/")
        auth_user = SimpleNamespace(is_authenticated=True)
        force_authenticate(request, user=auth_user)

        wrapper_serializer = MagicMock()
        wrapper_serializer.data = {"email": "student@example.com", "first_name": "Test"}
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

    def test_profile_patch_success_mocked(self):
        request = self.factory.patch(
            "/api/app/profile/",
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

        with patch("apps.users.api.views.UpdateProfileSerializer", return_value=serializer), patch(
            "apps.users.api.views.Profile.objects.get_or_create",
            return_value=(mock_profile, True),
        ):
            response = ProfileView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")


class RegisterViewIntegrationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('users:register')
        self.verify_url = reverse('users:register_verify')

    def _register_and_verify(self, email, password):
        with patch('apps.users.api.views.send_verification_email'):
            reg_response = self.client.post(
                self.register_url,
                {'email': email, 'password': password},
                format='json',
            )
        self.assertEqual(reg_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reg_response.data['status'], 'code_sent')

        from django.core.cache import cache
        from ..api.utils import encrypt_data as enc
        cache_key = f'pending_registration_email_{enc(email)}'
        cached = cache.get(cache_key)
        self.assertIsNotNone(cached, 'Registration code not found in cache')
        code = cached['code']

        verify_response = self.client.post(
            self.verify_url,
            {'email': email, 'code': code},
            format='json',
        )
        return verify_response

    def test_register_with_email_creates_user_in_db(self):
        response = self._register_and_verify('newuser@example.com', 'testpass123')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('role', response.data)

        self.assertTrue(User.objects.filter(
            email_cipher=encrypt_data('newuser@example.com')
        ).exists())

    def test_newly_registered_user_has_student_role(self):
        response = self._register_and_verify('student@example.com', 'testpass123')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'student')

        access_token = response.data['access_token']
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        self.assertEqual(decoded['role'], 'student')

        user = User.objects.get(email_cipher=encrypt_data('student@example.com'))
        self.assertEqual(user.role, User.ROLE_STUDENT)

    def test_register_duplicate_email(self):
        email = 'duplicate@example.com'
        User.objects.create_user(
            email_cipher=encrypt_data(email),
            password='testpass123'
        )

        with patch('apps.users.api.views.send_verification_email'):
            response = self.client.post(
                self.register_url,
                {'email': email, 'password': 'testpass123'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('email', response.data)


class LoginViewIntegrationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:login')
        self.email = 'test@example.com'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            email_cipher=encrypt_data(self.email),
            password=self.password
        )

    def test_login_with_email(self):

        data = {
            'email': self.email,
            'password': self.password
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('role', response.data)

    def test_login_returns_correct_role(self):

        teacher_email = 'teacher@example.com'
        teacher = User.objects.create_user(
            email_cipher=encrypt_data(teacher_email),
            password=self.password,
            role=User.ROLE_TEACHER
        )

        data = {
            'email': teacher_email,
            'password': self.password
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], User.ROLE_TEACHER)

        access_token = response.data['access_token']
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        self.assertEqual(decoded['role'], User.ROLE_TEACHER)


class RefreshTokenViewIntegrationTest(TestCase):


    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:token_refresh')
        self.user = User.objects.create_user(
            email_cipher=encrypt_data('test@example.com'),
            password='testpass123'
        )

    def test_refresh_token_success(self):

        tokens = get_tokens_for_user(self.user)

        data = {
            'refresh_token': tokens['refresh_token']
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)


class RecoverPasswordViewIntegrationTest(TestCase):


    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:recover_set')
        self.user = User.objects.create_user(
            email_cipher=encrypt_data('test@example.com'),
            password='oldpass123'
        )
        self.token = set_reset_token(self.user)

    def test_recover_password_success(self):

        new_password = 'newpass123'
        data = {
            'token': self.token,
            'password_hash': new_password
        }
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        self.assertIsNone(self.user.reset_token)
        self.assertIsNone(self.user.reset_token_expires)

    def test_recover_password_with_expired_token(self):

        self.user.reset_token_expires = timezone.now() - timedelta(hours=1)
        self.user.save()

        data = {
            'token': self.token,
            'password_hash': 'newpass123'
        }
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProfileViewIntegrationTest(TestCase):


    def setUp(self):
        self.client = APIClient()
        self.url = reverse('users:profile')
        self.user = User.objects.create_user(
            email_cipher=encrypt_data('test@example.com'),
            password='testpass123',
            first_name='Test',
            last_name='User'
        )


        tokens = get_tokens_for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access_token"]}')

    def test_get_profile_authenticated(self):

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email', response.data)
        self.assertIn('first_name', response.data)
        self.assertIn('last_name', response.data)

    def test_update_profile_first_name(self):

        data = {
            'first_name': 'Updated'
        }
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')

    def test_update_profile_gender(self):

        data = {
            'gender': 'Мужской'
        }
        response = self.client.patch(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.gender, 'Мужской')

    def test_profile_auto_created(self):

        Profile.objects.filter(user=self.user).delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
