from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.courses.tests.test_models import create_test_course, create_test_user
from apps.payments.models import Payment, PaymentItem
from apps.payments.services import MockYooKassaService, YooKassaPaymentResponse


class MockYooKassaServiceTests(SimpleTestCase):

    def test_create_payment_returns_pending_status(self):
        result = MockYooKassaService.create_payment(amount=Decimal("999.00"))
        self.assertEqual(result.status, "pending")
        self.assertFalse(result.paid)

    def test_create_payment_uses_provided_idempotency_key(self):
        key = "my-unique-key-123"
        result = MockYooKassaService.create_payment(amount=Decimal("100.00"), idempotency_key=key)
        self.assertIn(key, result.confirmation_url)
        self.assertEqual(result.id, key)

    def test_create_payment_generates_uuid_when_no_key(self):
        result = MockYooKassaService.create_payment(amount=Decimal("100.00"))
        self.assertIsNotNone(result.id)
        self.assertIsNotNone(result.confirmation_url)

    def test_create_payment_includes_description(self):
        result = MockYooKassaService.create_payment(
            amount=Decimal("100.00"), description="Order #42"
        )
        self.assertEqual(result.description, "Order #42")

    def test_create_payment_amount_value_matches(self):
        result = MockYooKassaService.create_payment(amount=Decimal("500.50"))
        self.assertEqual(result.amount_value, "500.50")

    def test_create_payment_currency_default_rub(self):
        result = MockYooKassaService.create_payment(amount=Decimal("1.00"))
        self.assertEqual(result.amount_currency, "RUB")

    def test_fetch_payment_status_returns_succeeded_or_canceled(self):
        result = MockYooKassaService.fetch_payment_status("some-uuid")
        self.assertIn(result["status"], ("succeeded", "canceled"))
        self.assertIn(result["paid"], (True, False))
        self.assertEqual(result["id"], "some-uuid")

    def test_fetch_payment_status_paid_matches_status(self):
        for _ in range(20):
            result = MockYooKassaService.fetch_payment_status("uuid")
            if result["status"] == "succeeded":
                self.assertTrue(result["paid"])
            else:
                self.assertFalse(result["paid"])

    def test_capture_payment_returns_succeeded(self):
        result = MockYooKassaService.capture_payment("some-uuid")
        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["paid"])
        self.assertEqual(result["id"], "some-uuid")

    def test_refund_payment_returns_refund_data(self):
        result = MockYooKassaService.refund_payment("pay-uuid", Decimal("50.00"))
        self.assertEqual(result["payment_id"], "pay-uuid")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["amount"]["value"], "50.00")
        self.assertEqual(result["amount"]["currency"], "RUB")
        self.assertIn("id", result)

    def test_refund_creates_new_refund_id(self):
        r1 = MockYooKassaService.refund_payment("p", Decimal("1.00"))
        r2 = MockYooKassaService.refund_payment("p", Decimal("1.00"))
        self.assertNotEqual(r1["id"], r2["id"])


class PaymentModelTests(TestCase):

    def setUp(self):
        self.user = create_test_user(email="pay_model_st@test.local", role="student")

    def test_payment_default_status_is_pending(self):
        p = Payment.objects.create(user=self.user, total_sum=Decimal("100.00"))
        self.assertEqual(p.status, "pending")

    def test_payment_str_contains_payment_id(self):
        p = Payment.objects.create(user=self.user, total_sum=Decimal("200.00"))
        self.assertIn(str(p.payment_id), str(p))

    def test_payment_mock_yookassa_id_is_uuid(self):
        p = Payment.objects.create(user=self.user, total_sum=Decimal("100.00"))
        self.assertIsNotNone(p.mock_yookassa_id)
        self.assertIsNotNone(str(p.mock_yookassa_id))

    def test_payment_paid_at_null_by_default(self):
        p = Payment.objects.create(user=self.user, total_sum=Decimal("100.00"))
        self.assertIsNone(p.paid_at)

    def test_payment_ordering_newest_first(self):
        p1 = Payment.objects.create(user=self.user, total_sum=Decimal("100.00"))
        p2 = Payment.objects.create(user=self.user, total_sum=Decimal("200.00"))
        payments = list(Payment.objects.filter(user=self.user))
        self.assertEqual(payments[0], p2)

    def test_payment_status_choices(self):
        statuses = [s[0] for s in Payment.STATUS_CHOICES]
        for expected in ("pending", "approved", "success", "failed", "refunded"):
            self.assertIn(expected, statuses)

    def test_payment_cascade_deleted_with_user(self):
        p = Payment.objects.create(user=self.user, total_sum=Decimal("100.00"))
        pid = p.payment_id
        self.user.delete()
        self.assertFalse(Payment.objects.filter(payment_id=pid).exists())


class PaymentItemModelTests(TestCase):

    def setUp(self):
        self.user = create_test_user(email="pay_item_st@test.local", role="student")
        self.course = create_test_course(title="Item Course")
        self.payment = Payment.objects.create(user=self.user, total_sum=Decimal("100.00"))

    def test_payment_item_str_contains_course_and_price(self):
        item = PaymentItem.objects.create(
            payment=self.payment, course=self.course, price=Decimal("100.00")
        )
        s = str(item)
        self.assertIn("100", s)

    def test_payment_item_unique_per_payment_and_course(self):
        PaymentItem.objects.create(
            payment=self.payment, course=self.course, price=Decimal("100.00")
        )
        from django.db import IntegrityError
        from django.db import transaction as db_transaction

        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                PaymentItem.objects.create(
                    payment=self.payment, course=self.course, price=Decimal("50.00")
                )

    def test_payment_item_cascade_deleted_with_payment(self):
        item = PaymentItem.objects.create(
            payment=self.payment, course=self.course, price=Decimal("100.00")
        )
        iid = item.pk
        self.payment.delete()
        self.assertFalse(PaymentItem.objects.filter(pk=iid).exists())

    def test_payment_item_cascade_deleted_with_course(self):
        item = PaymentItem.objects.create(
            payment=self.payment, course=self.course, price=Decimal("100.00")
        )
        iid = item.pk
        self.course.delete()
        self.assertFalse(PaymentItem.objects.filter(pk=iid).exists())
