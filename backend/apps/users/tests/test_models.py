import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from ..api.utils.crypto_utils import encrypt_data
from ..models import Profile, User


class UserModelTest(TestCase):

    def setUp(self):
        self.email = "test@example.com"
        self.encrypted_email = encrypt_data(self.email)
        self.password = "testpass123"

    def test_create_user_with_email(self):
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        self.assertIsNotNone(user)
        self.assertEqual(user.email_cipher, self.encrypted_email)
        self.assertTrue(user.check_password(self.password))

    def test_user_default_role_is_student(self):
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        self.assertEqual(user.role, User.ROLE_STUDENT)

    def test_user_role_choices(self):
        student = User.objects.create_user(
            email_cipher=encrypt_data("student@example.com"),
            password=self.password,
            role=User.ROLE_STUDENT,
        )
        self.assertEqual(student.role, "student")
        teacher = User.objects.create_user(
            email_cipher=encrypt_data("teacher@example.com"),
            password=self.password,
            role=User.ROLE_TEACHER,
        )
        self.assertEqual(teacher.role, "teacher")
        moderator = User.objects.create_user(
            email_cipher=encrypt_data("moderator@example.com"),
            password=self.password,
            role=User.ROLE_MODERATOR,
        )
        self.assertEqual(moderator.role, "moderator")

    def test_user_is_student_method(self):
        user = User.objects.create_user(
            email_cipher=self.encrypted_email, password=self.password, role=User.ROLE_STUDENT
        )
        self.assertTrue(user.is_student())
        self.assertFalse(user.is_teacher())
        self.assertFalse(user.is_moderator())

    def test_user_is_teacher_method(self):
        user = User.objects.create_user(
            email_cipher=self.encrypted_email, password=self.password, role=User.ROLE_TEACHER
        )
        self.assertFalse(user.is_student())
        self.assertTrue(user.is_teacher())
        self.assertFalse(user.is_moderator())

    def test_user_is_moderator_method(self):
        user = User.objects.create_user(
            email_cipher=self.encrypted_email, password=self.password, role=User.ROLE_MODERATOR
        )
        self.assertFalse(user.is_student())
        self.assertFalse(user.is_teacher())
        self.assertTrue(user.is_moderator())

    def test_user_default_fields(self):
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertEqual(user.reset_token, "")
        self.assertIsNone(user.reset_token_expires)
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertIsNone(user.phone_cipher)
        self.assertIsNotNone(user.date_joined)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_user_with_phone(self):
        phone = "+79991234567"
        encrypted_phone = encrypt_data(phone)
        user = User.objects.create_user(
            email_cipher=self.encrypted_email, phone_cipher=encrypted_phone, password=self.password
        )
        self.assertEqual(user.phone_cipher, encrypted_phone)

    def test_user_unique_email(self):
        User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        with self.assertRaises(Exception):
            User.objects.create_user(email_cipher=self.encrypted_email, password="anotherpass")

    def test_user_reset_token_fields(self):
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        self.assertEqual(user.reset_token, "")
        self.assertIsNone(user.reset_token_expires)
        token = "test_reset_token_123"
        expires = timezone.now() + timezone.timedelta(hours=24)
        user.reset_token = token
        user.reset_token_expires = expires
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.reset_token, token)
        self.assertEqual(user.reset_token_expires, expires)

    def test_user_password_hashing(self):
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.check_password("wrongpassword"))

    def test_user_str_representation(self):
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        str_repr = str(user)
        self.assertIn(str(user.id), str_repr)

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(
            email_cipher=self.encrypted_email, password=self.password
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

    def test_user_date_joined_auto_set(self):
        before = timezone.now()
        user = User.objects.create_user(email_cipher=self.encrypted_email, password=self.password)
        after = timezone.now()
        self.assertIsNotNone(user.date_joined)
        self.assertGreaterEqual(user.date_joined, before)
        self.assertLessEqual(user.date_joined, after)

    def test_user_ordering(self):
        user1 = User.objects.create_user(
            email_cipher=encrypt_data("user1@example.com"), password=self.password
        )
        user2 = User.objects.create_user(
            email_cipher=encrypt_data("user2@example.com"), password=self.password
        )
        users = list(User.objects.all())
        self.assertEqual(users[0].id, user2.id)
        self.assertEqual(users[1].id, user1.id)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email_cipher=encrypt_data("test@example.com"), password="testpass123"
        )
        self.storage_patcher = patch("django.core.files.storage.default_storage._wrapped")
        self.storage_patcher.start()

    def tearDown(self):
        self.storage_patcher.stop()

    def test_profile_creation(self):
        profile = Profile.objects.create(user=self.user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user, self.user)

    def test_profile_default_fields(self):
        profile = Profile.objects.create(user=self.user)
        self.assertIsNone(profile.birthday)
        self.assertEqual(profile.gender, "")
        self.assertEqual(profile.avatar_url, "")

    def test_profile_gender_choices(self):
        profile = Profile.objects.create(user=self.user, gender="М")
        self.assertEqual(profile.gender, "М")
        user2 = User.objects.create_user(
            email_cipher=encrypt_data("user2@example.com"), password="testpass123"
        )
        profile2 = Profile.objects.create(user=user2, gender="Ж")
        self.assertEqual(profile2.gender, "Ж")

    def test_profile_one_to_one_relationship(self):
        profile = Profile.objects.create(user=self.user)
        self.assertEqual(self.user.profile, profile)
        self.assertEqual(profile.user, self.user)
