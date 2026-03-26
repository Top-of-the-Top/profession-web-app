from django.test import TestCase, SimpleTestCase
from rest_framework.exceptions import ValidationError
from unittest.mock import MagicMock, patch
from ..models import User
from ..api.serializers import (
    RegisterSerializer,
    LoginSerializer,
    UpdateProfileSerializer,
)
from ..api.utils import encrypt_data

class RegisterSerializerUnitTest(SimpleTestCase):


    def test_valid_registration_with_email(self):
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        with patch.object(RegisterSerializer, 'validate', return_value=data):
            serializer = RegisterSerializer(data=data)
            with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
                mock_filter.return_value.exists.return_value = False
                self.assertTrue(serializer.is_valid())

    def test_valid_registration_with_phone(self):
        data = {
            'phone_number': '+79991234567',
            'password': 'testpass123'
        }

        with patch.object(RegisterSerializer, 'validate', return_value=data):
            serializer = RegisterSerializer(data=data)
            with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
                mock_filter.return_value.exists.return_value = False
                self.assertTrue(serializer.is_valid())

    def test_registration_without_contact(self):
        data = {
            'password': 'testpass123'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_registration_with_short_password(self):
        data = {
            'email': 'test@example.com',
            'password': 'short'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_registration_encrypts_email(self):
        email = 'test@example.com'
        data = {
            'email': email,
            'password': 'testpass123'
        }

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = False
            serializer = RegisterSerializer(data=data)
            self.assertTrue(serializer.is_valid())

            self.assertIn('email_cipher', serializer.validated_data)
            self.assertNotEqual(serializer.validated_data['email_cipher'], email)

    def test_registration_encrypts_phone(self):
        phone = '+79991234567'
        data = {
            'phone_number': phone,
            'password': 'testpass123'
        }

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = False
            serializer = RegisterSerializer(data=data)
            self.assertTrue(serializer.is_valid())

            # Check that phone_cipher is in validated data
            self.assertIn('phone_cipher', serializer.validated_data)
            # Check that it's encrypted (not plain text)
            self.assertNotEqual(serializer.validated_data['phone_cipher'], phone)


class LoginSerializerUnitTest(SimpleTestCase):


    def test_login_without_contact(self):
        """Test login fails without email or phone"""
        data = {
            'password': 'testpass123'
        }
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_login_with_wrong_password(self):
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        mock_user = MagicMock()
        mock_user.check_password.return_value = False

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.first.return_value = mock_user
            serializer = LoginSerializer(data=data)
            self.assertFalse(serializer.is_valid())

    def test_login_with_nonexistent_email(self):
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.first.return_value = None
            serializer = LoginSerializer(data=data)
            self.assertFalse(serializer.is_valid())

    def test_valid_login_with_email(self):
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        mock_user = MagicMock()
        mock_user.check_password.return_value = True

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.first.return_value = mock_user
            serializer = LoginSerializer(data=data)
            self.assertTrue(serializer.is_valid())
            self.assertEqual(serializer.validated_data['user'], mock_user)


class UpdateProfileSerializerUnitTest(SimpleTestCase):


    def test_update_first_name(self):
        """Test updating first name"""
        data = {
            'first_name': 'Updated'
        }
        mock_user = MagicMock()
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': mock_user}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_email(self):
        data = {
            'email': 'newemail@example.com'
        }
        mock_user = MagicMock()
        mock_user.id = 1

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.exclude.return_value.exists.return_value = False
            serializer = UpdateProfileSerializer(
                data=data,
                context={'user': mock_user}
            )
            self.assertTrue(serializer.is_valid())
            self.assertIn('email_cipher', serializer.validated_data)

    def test_update_valid_gender(self):
        data = {
            'gender': 'Мужской'
        }
        mock_user = MagicMock()
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': mock_user}
        )
        self.assertTrue(serializer.is_valid())

        data = {
            'gender': 'Женский'
        }
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': mock_user}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_invalid_gender(self):
        data = {
            'gender': 'Invalid'
        }
        mock_user = MagicMock()
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': mock_user}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('gender', serializer.errors)

    def test_update_birthday(self):
        data = {
            'birthday': '1990-01-01'
        }
        mock_user = MagicMock()
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': mock_user}
        )
        self.assertTrue(serializer.is_valid())

    def test_update_phone_number(self):
        data = {
            'phone_number': '+79991234567'
        }
        mock_user = MagicMock()
        mock_user.id = 1

        with patch('apps.users.api.serializers.User.objects.filter') as mock_filter:
            mock_filter.return_value.exclude.return_value.exists.return_value = False
            serializer = UpdateProfileSerializer(
                data=data,
                context={'user': mock_user}
            )
            self.assertTrue(serializer.is_valid())
            self.assertIn('phone_cipher', serializer.validated_data)

class RegisterSerializerIntegrationTest(TestCase):


    def test_registration_duplicate_email(self):
        email = 'duplicate@example.com'
        User.objects.create_user(
            email_cipher=encrypt_data(email),
            password='testpass123'
        )

        data = {
            'email': email,
            'password': 'testpass123'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_registration_duplicate_phone(self):

        phone = '+79991234567'
        User.objects.create_user(
            phone_cipher=encrypt_data(phone),
            password='testpass123'
        )

        data = {
            'phone_number': phone,
            'password': 'testpass123'
        }
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class LoginSerializerIntegrationTest(TestCase):

    def setUp(self):
        """Create test user"""
        self.email = 'test@example.com'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            email_cipher=encrypt_data(self.email),
            password=self.password
        )

    def test_valid_login_with_email(self):

        data = {
            'email': self.email,
            'password': self.password
        }
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], self.user)

    def test_login_with_phone(self):

        phone = '+79991234567'
        user = User.objects.create_user(
            phone_cipher=encrypt_data(phone),
            password=self.password
        )

        data = {
            'phone_number': phone,
            'password': self.password
        }
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], user)


class UpdateProfileSerializerIntegrationTest(TestCase):


    def setUp(self):
        self.user = User.objects.create_user(
            email_cipher=encrypt_data('test@example.com'),
            password='testpass123'
        )

    def test_update_duplicate_email(self):

        other_email = 'other@example.com'
        User.objects.create_user(
            email_cipher=encrypt_data(other_email),
            password='testpass123'
        )

        data = {
            'email': other_email
        }
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': self.user}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_update_duplicate_phone(self):

        other_phone = '+79991234567'
        User.objects.create_user(
            phone_cipher=encrypt_data(other_phone),
            password='testpass123'
        )

        data = {
            'phone_number': other_phone
        }
        serializer = UpdateProfileSerializer(
            data=data,
            context={'user': self.user}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)
