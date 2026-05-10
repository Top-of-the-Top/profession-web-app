from datetime import datetime, timedelta
from unittest.mock import MagicMock

import jwt
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from ..api.utils.crypto_utils import decrypt_data, encrypt_data
from ..api.utils.token_utils import generate_reset_token, get_tokens_for_user, set_reset_token
from ..models import User


class EncryptionUnitTest(SimpleTestCase):

    def test_correct_encoding(self):
        email = "test@example.com"
        encoded_email = encrypt_data(email)
        decoded_email = decrypt_data(encoded_email)
        self.assertEqual(email, decoded_email)

    def test_incorrect_encoding(self):
        email = "test@example.com"
        encoded_email = encrypt_data(email + "incorrect")
        decoded_email = decrypt_data(encoded_email)
        self.assertNotEqual(email, decoded_email)

    def test_empty_string_encryption(self):
        result = encrypt_data("")
        self.assertEqual(result, "")

    def test_empty_string_decryption(self):
        result = decrypt_data("")
        self.assertEqual(result, "")

    def test_encryption_consistency(self):
        data = "consistent_data"
        encrypted1 = encrypt_data(data)
        encrypted2 = encrypt_data(data)
        self.assertEqual(encrypted1, encrypted2)

    def test_decryption_invalid_data(self):
        result = decrypt_data("invalid_base64_data")
        self.assertEqual(result, "")

    def test_encryption_special_characters(self):
        data = "test+special@chars#123"
        encrypted = encrypt_data(data)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(data, decrypted)

    def test_encryption_unicode(self):
        data = "тест@пример.рф"
        encrypted = encrypt_data(data)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(data, decrypted)


class ResetTokenUnitTest(SimpleTestCase):

    def test_generate_reset_token(self):
        token = generate_reset_token()
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 20)

    def test_generate_reset_token_uniqueness(self):
        token1 = generate_reset_token()
        token2 = generate_reset_token()
        self.assertNotEqual(token1, token2)


class JWTTokenUnitTest(SimpleTestCase):

    def test_get_tokens_for_user_structure(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "student"
        tokens = get_tokens_for_user(mock_user)
        self.assertIn("access_token", tokens)
        self.assertIn("access_expires_at", tokens)
        self.assertIn("refresh_token", tokens)
        self.assertIn("refresh_expires_at", tokens)
        self.assertIn("role", tokens)

    def test_get_tokens_for_student(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "student"
        tokens = get_tokens_for_user(mock_user)
        self.assertEqual(tokens["role"], "student")
        self.assertIsNotNone(tokens["access_token"])
        self.assertIsNotNone(tokens["refresh_token"])

    def test_get_tokens_for_teacher(self):
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.role = "teacher"
        tokens = get_tokens_for_user(mock_user)
        self.assertEqual(tokens["role"], "teacher")

    def test_get_tokens_for_moderator(self):
        mock_user = MagicMock()
        mock_user.id = 3
        mock_user.role = "moderator"
        tokens = get_tokens_for_user(mock_user)
        self.assertEqual(tokens["role"], "moderator")

    def test_jwt_contains_role_claim(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "student"
        tokens = get_tokens_for_user(mock_user)
        access_token = tokens["access_token"]
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        self.assertIn("role", decoded)
        self.assertEqual(decoded["role"], "student")

    def test_jwt_refresh_token_contains_role(self):
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.role = "teacher"
        tokens = get_tokens_for_user(mock_user)
        refresh_token = tokens["refresh_token"]
        decoded = jwt.decode(refresh_token, options={"verify_signature": False})
        self.assertIn("role", decoded)
        self.assertEqual(decoded["role"], "teacher")

    def test_token_expiry_timestamps(self):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "student"
        tokens = get_tokens_for_user(mock_user)
        access_expires = datetime.fromisoformat(tokens["access_expires_at"])
        refresh_expires = datetime.fromisoformat(tokens["refresh_expires_at"])
        self.assertGreater(refresh_expires, access_expires)

    def test_token_user_id_matches(self):
        mock_user = MagicMock()
        mock_user.id = 42
        mock_user.role = "student"
        tokens = get_tokens_for_user(mock_user)
        decoded = jwt.decode(tokens["access_token"], options={"verify_signature": False})
        self.assertEqual(int(decoded["user_id"]), 42)


class ResetTokenIntegrationTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("test@example.com"), password="testpass123"
        )

    def test_set_reset_token(self):
        token = set_reset_token(self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.reset_token, token)
        self.assertIsNotNone(self.user.reset_token_expires)
        self.assertGreater(self.user.reset_token_expires, timezone.now())

    def test_set_reset_token_custom_validity(self):
        valid_hours = 48
        token = set_reset_token(self.user, valid_hours=valid_hours)
        self.user.refresh_from_db()
        expected_expiry = timezone.now() + timedelta(hours=valid_hours)
        time_diff = abs((self.user.reset_token_expires - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)

    def test_reset_token_expiry_default(self):
        set_reset_token(self.user)
        self.user.refresh_from_db()
        expected_expiry = timezone.now() + timedelta(hours=24)
        time_diff = abs((self.user.reset_token_expires - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)


class JWTTokenIntegrationTest(TestCase):

    def setUp(self):
        self.student_user = User.objects.create_user(
            email_cipher=encrypt_data("student@example.com"),
            password="testpass123",
            role=User.ROLE_STUDENT,
        )
        self.teacher_user = User.objects.create_user(
            email_cipher=encrypt_data("teacher@example.com"),
            password="testpass123",
            role=User.ROLE_TEACHER,
        )

    def test_newly_registered_user_has_student_role(self):
        new_user = User.objects.create_user(
            email_cipher=encrypt_data("newuser@example.com"), password="testpass123"
        )
        self.assertEqual(new_user.role, User.ROLE_STUDENT)
        tokens = get_tokens_for_user(new_user)
        self.assertEqual(tokens["role"], User.ROLE_STUDENT)

    def test_user_without_explicit_role_defaults_to_student(self):
        user = User.objects.create_user(
            email_cipher=encrypt_data("default@example.com"), password="testpass123"
        )
        tokens = get_tokens_for_user(user)
        decoded = jwt.decode(tokens["access_token"], options={"verify_signature": False})
        self.assertEqual(decoded["role"], "student")
