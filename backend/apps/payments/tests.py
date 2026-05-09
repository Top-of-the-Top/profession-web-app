import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import caches
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.carts.api.views import cart_hot_cache_key
from apps.carts.models import Cart, CartItem
from apps.courses.api.utils.cache_utils import purchased_courses_cache_key
from apps.courses.models import PurchasedCourse
from apps.courses.tests.test_models import create_test_course, create_test_user, publish_course_tree
from apps.payments.models import Payment, PaymentItem
from apps.payments.tasks import _handle_failure, process_payment_task
from apps.users.api.utils.token_utils import get_tokens_for_user


class PaymentTaskUnitTests(SimpleTestCase):

    def setUp(self):
        self.mock_payment = MagicMock(spec=Payment)
        self.mock_payment.payment_id = 1
        self.mock_payment.user_id = 1
        self.mock_payment.user = MagicMock()
        self.mock_payment.user.id = 1
        self.mock_payment.status = "pending"
        self.mock_payment.mock_yookassa_id = uuid.uuid4()

    def test_process_payment_task_success(self):
        mock_fetch = MagicMock()
        mock_fetch.return_value = {"paid": True}
        mock_handle_success = MagicMock()
        mock_handle_success.return_value = {
            "status": "success",
            "payment_id": 1,
        }
        with (
            patch("apps.payments.models.Payment") as mock_payment_class,
            patch(
                "apps.payments.services.MockYooKassaService.fetch_payment_status",
                mock_fetch,
            ),
            patch("apps.payments.tasks._handle_success", mock_handle_success),
        ):
            mock_payment_class.objects.select_related.return_value.get.return_value = (
                self.mock_payment
            )
            result = process_payment_task(1)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["payment_id"], 1)

    def test_process_payment_task_payment_not_found(self):
        with (
            patch("apps.payments.models.Payment") as mock_payment_class,
            patch("apps.payments.tasks.logger") as mock_logger,
        ):
            mock_payment_class.DoesNotExist = Payment.DoesNotExist
            mock_payment_class.objects.select_related.return_value.get.side_effect = (
                Payment.DoesNotExist
            )
            result = process_payment_task(999)
            self.assertEqual(result["status"], "error")
            mock_logger.error.assert_called_once()

    def test_process_payment_task_already_processed(self):
        self.mock_payment.status = "success"
        with (
            patch("apps.payments.models.Payment") as mock_payment_class,
            patch("apps.payments.tasks.logger") as mock_logger,
        ):
            mock_payment_class.objects.select_related.return_value.get.return_value = (
                self.mock_payment
            )
            result = process_payment_task(1)
            self.assertEqual(result["status"], "skipped")
            mock_logger.info.assert_called_once()

    def test_handle_failure_with_retry(self):
        mock_payment = MagicMock()
        mock_payment.status = "approved"
        mock_payment.save = MagicMock()
        mock_task = MagicMock()
        mock_task.request.retries = 2
        mock_task.max_retries = 5
        mock_task.retry.side_effect = Exception("Retry")
        with patch("apps.payments.tasks.logger"):
            with self.assertRaises(Exception):
                _handle_failure(mock_task, mock_payment)
            self.assertEqual(mock_payment.status, "pending")
            self.assertEqual(mock_payment.save.call_count, 2)

    def test_handle_failure_max_retries(self):
        mock_payment = MagicMock()
        mock_payment.payment_id = 1
        mock_payment.status = "approved"
        mock_payment.save = MagicMock()
        mock_task = MagicMock()
        mock_task.request.retries = 5
        mock_task.max_retries = 5
        with patch("apps.payments.tasks.logger"):
            result = _handle_failure(mock_task, mock_payment)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["payment_id"], 1)
            self.assertEqual(mock_payment.status, "failed")
            mock_payment.save.assert_called_once()


class PaymentsApiHttpTests(TestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = create_test_user(email="payments_http_student@test.com", role="student")
        caches["hot"].delete(cart_hot_cache_key(self.user.id))
        caches["default"].delete(purchased_courses_cache_key(self.user.id))
        self.course = create_test_course(title="Payments Api Course")
        publish_course_tree(self.course)

    def _auth(self, user=None):
        user = user or self.user
        tokens = get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def _add_to_cart(self, slug):
        r = self.client.post(f"/api/v1/carts/add/{slug}/")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

    def test_cart_pay_requires_auth(self):
        r = self.client.post("/api/v1/carts/pay/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_pay_empty_cart_returns_400(self):
        self._auth()
        r = self.client.post("/api/v1/carts/pay/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Корзина пуста", r.data["error"])

    @patch("apps.payments.api.views.process_payment_task.apply_async")
    def test_cart_pay_already_purchased_returns_400(self, mock_apply):
        payment = Payment.objects.create(
            user=self.user,
            total_sum=Decimal(str(self.course.price)),
            status="success",
        )
        PurchasedCourse.objects.create(
            user=self.user,
            course=self.course,
            payment=payment,
            access_expires_at=timezone.now() + timedelta(days=30),
        )
        self._auth()
        self._add_to_cart(self.course.slug)
        r = self.client.post("/api/v1/carts/pay/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("уже куплены", r.data["error"])
        cid_str = str(self.course.course_id)
        self.assertTrue(any(str(x) == cid_str for x in r.data["course_ids"]))
        mock_apply.assert_not_called()

    @patch("apps.payments.api.views.process_payment_task.apply_async")
    def test_cart_pay_success_creates_records_clears_cart_returns_204(self, mock_apply):
        self._auth()
        self._add_to_cart(self.course.slug)
        r = self.client.post("/api/v1/carts/pay/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        mock_apply.assert_called_once()
        payment_id = mock_apply.call_args.kwargs["args"][0]
        payment = Payment.objects.get(payment_id=payment_id)
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.total_sum, Decimal(str(self.course.price)))
        self.assertTrue(payment.mock_payment_url)
        self.assertEqual(PaymentItem.objects.filter(payment=payment).count(), 1)
        self.assertTrue(PurchasedCourse.objects.filter(user=self.user, course=self.course).exists())
        cart = Cart.objects.get(user=self.user)
        self.assertFalse(CartItem.objects.filter(cart=cart).exists())

    def test_payment_list_requires_auth(self):
        r = self.client.get("/api/v1/payments/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_list_only_current_user(self):
        other = create_test_user(email="payments_http_other@test.com", role="student")
        caches["hot"].delete(cart_hot_cache_key(other.id))
        caches["default"].delete(purchased_courses_cache_key(other.id))
        p_self = Payment.objects.create(
            user=self.user, total_sum=Decimal("100.00"), status="pending"
        )
        p_other = Payment.objects.create(user=other, total_sum=Decimal("200.00"), status="pending")
        self._auth(self.user)
        r = self.client.get("/api/v1/payments/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [row["payment_id"] for row in r.data]
        self.assertIn(p_self.payment_id, ids)
        self.assertNotIn(p_other.payment_id, ids)

    def test_payment_detail_requires_auth(self):
        r = self.client.get("/api/v1/payments/1/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_detail_not_found_for_other_user(self):
        owner = create_test_user(email="payments_owner@test.com", role="student")
        caches["hot"].delete(cart_hot_cache_key(owner.id))
        caches["default"].delete(purchased_courses_cache_key(owner.id))
        p = Payment.objects.create(user=owner, total_sum=Decimal("50.00"), status="pending")
        self._auth(self.user)
        r = self.client.get(f"/api/v1/payments/{p.payment_id}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_detail_success(self):
        p = Payment.objects.create(user=self.user, total_sum=Decimal("9000.00"), status="pending")
        PaymentItem.objects.create(
            payment=p,
            course=self.course,
            price=Decimal(str(self.course.price)),
        )
        self._auth()
        r = self.client.get(f"/api/v1/payments/{p.payment_id}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["payment_id"], p.payment_id)
        self.assertEqual(len(r.data["items"]), 1)
        self.assertEqual(r.data["items"][0]["course"]["slug"], self.course.slug)
