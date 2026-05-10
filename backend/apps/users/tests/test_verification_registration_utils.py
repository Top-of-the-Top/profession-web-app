from datetime import timedelta

from django.core.cache import cache
from django.test import SimpleTestCase
from django.utils import timezone

from apps.users.api.errors import VerificationError
from apps.users.api.utils.registration_utils import (
    check_contact_rate_limit,
    generate_registration_code,
    verify_registration_code,
)
from apps.users.api.utils.verification_utils import (
    delete_verification_code,
    generate_verification_code_for_user,
    get_verification_code_for_user,
    verify_code,
)


class GenerateVerificationCodeTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_returns_6_digit_string(self):
        code = generate_verification_code_for_user(1, "email", "new@test.com")
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_code_stored_in_cache(self):
        code = generate_verification_code_for_user(2, "phone", "+79001234567")
        data = get_verification_code_for_user(2, "phone")
        self.assertIsNotNone(data)
        self.assertEqual(data["code"], code)
        self.assertEqual(data["new_contact"], "+79001234567")

    def test_delete_removes_code(self):
        generate_verification_code_for_user(3, "email", "x@test.com")
        delete_verification_code(3, "email")
        self.assertIsNone(get_verification_code_for_user(3, "email"))


class VerifyCodeTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_correct_code_returns_new_contact(self):
        code = generate_verification_code_for_user(10, "email", "new@test.com")
        result = verify_code(10, "email", code)
        self.assertEqual(result, "new@test.com")

    def test_wrong_code_raises_invalid(self):
        generate_verification_code_for_user(11, "email", "x@test.com")
        with self.assertRaises(VerificationError) as ctx:
            verify_code(11, "email", "000000")
        self.assertEqual(ctx.exception.code, "invalid")

    def test_no_code_raises_not_found(self):
        with self.assertRaises(VerificationError) as ctx:
            verify_code(99, "email", "123456")
        self.assertEqual(ctx.exception.code, "not_found")

    def test_too_many_attempts_raises_error(self):
        code = generate_verification_code_for_user(12, "email", "y@test.com")
        attempts_key = "verify_attempts_12_email"
        cache.set(attempts_key, 5, timeout=300)
        with self.assertRaises(VerificationError) as ctx:
            verify_code(12, "email", "000000")
        self.assertEqual(ctx.exception.code, "too_many_attempts")

    def test_expired_code_raises_expired(self):
        old_time = (timezone.now() - timedelta(minutes=10)).isoformat()
        cache_key = "verification_code_20_email"
        cache.set(
            cache_key,
            {
                "code": "123456",
                "new_contact": "e@test.com",
                "created_at": old_time,
            },
            timeout=300,
        )
        with self.assertRaises(VerificationError) as ctx:
            verify_code(20, "email", "123456")
        self.assertEqual(ctx.exception.code, "expired")

    def test_correct_code_deletes_from_cache(self):
        code = generate_verification_code_for_user(13, "email", "z@test.com")
        verify_code(13, "email", code)
        self.assertIsNone(get_verification_code_for_user(13, "email"))

    def test_wrong_code_increments_attempts_counter(self):
        generate_verification_code_for_user(14, "email", "a@test.com")
        try:
            verify_code(14, "email", "000000")
        except VerificationError:
            pass
        attempts = cache.get("verify_attempts_14_email", 0)
        self.assertEqual(attempts, 1)


class GenerateRegistrationCodeTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_returns_6_digit_code(self):
        code = generate_registration_code("test@test.com", "pass123", "email")
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_code_stored_with_hashed_password(self):
        code = generate_registration_code("+79001234567", "mypass", "phone")
        from apps.users.api.utils.crypto_utils import encrypt_data

        cipher = encrypt_data("+79001234567")
        key = f"pending_registration_phone_{cipher}"
        data = cache.get(key)
        self.assertIsNotNone(data)
        self.assertIn("password_hash", data)
        self.assertNotEqual(data["password_hash"], "mypass")

    def test_verify_correct_code_returns_contact_data(self):
        code = generate_registration_code("reg@test.com", "mypassword", "email")
        result = verify_registration_code("reg@test.com", code, "email")
        self.assertEqual(result["contact"], "reg@test.com")
        self.assertEqual(result["contact_type"], "email")
        self.assertIn("password_hash", result)

    def test_verify_wrong_code_raises_invalid(self):
        generate_registration_code("wrong@test.com", "pass", "email")
        with self.assertRaises(VerificationError) as ctx:
            verify_registration_code("wrong@test.com", "000000", "email")
        self.assertEqual(ctx.exception.code, "invalid")

    def test_verify_no_code_raises_not_found(self):
        with self.assertRaises(VerificationError) as ctx:
            verify_registration_code("nobody@test.com", "123456", "email")
        self.assertEqual(ctx.exception.code, "not_found")

    def test_verify_expired_code_raises_expired(self):
        from apps.users.api.utils.crypto_utils import encrypt_data

        old_time = (timezone.now() - timedelta(minutes=10)).isoformat()
        cipher = encrypt_data("exp@test.com")
        key = f"pending_registration_email_{cipher}"
        cache.set(
            key,
            {
                "code": "111111",
                "contact": "exp@test.com",
                "contact_type": "email",
                "password_hash": "hashed",
                "created_at": old_time,
            },
            timeout=300,
        )
        with self.assertRaises(VerificationError) as ctx:
            verify_registration_code("exp@test.com", "111111", "email")
        self.assertEqual(ctx.exception.code, "expired")

    def test_verify_too_many_attempts_raises(self):
        code = generate_registration_code("limit@test.com", "pass", "email")
        from apps.users.api.utils.crypto_utils import encrypt_data

        cipher = encrypt_data("limit@test.com")
        attempts_key = f"reg_verify_attempts_email_{cipher}"
        cache.set(attempts_key, 5, timeout=300)
        with self.assertRaises(VerificationError) as ctx:
            verify_registration_code("limit@test.com", "000000", "email")
        self.assertEqual(ctx.exception.code, "too_many_attempts")


class CheckContactRateLimitTests(SimpleTestCase):

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_first_call_allowed(self):
        ok, retry = check_contact_rate_limit("+79001234567", "phone")
        self.assertTrue(ok)
        self.assertEqual(retry, 0)

    def test_second_call_blocked(self):
        check_contact_rate_limit("dup@test.com", "email")
        ok, retry = check_contact_rate_limit("dup@test.com", "email")
        self.assertFalse(ok)
        self.assertGreater(retry, 0)

    def test_different_contacts_not_blocked(self):
        check_contact_rate_limit("a@test.com", "email")
        ok, _ = check_contact_rate_limit("b@test.com", "email")
        self.assertTrue(ok)

    def test_different_types_not_blocked(self):
        check_contact_rate_limit("same", "phone")
        ok, _ = check_contact_rate_limit("same", "email")
        self.assertTrue(ok)
