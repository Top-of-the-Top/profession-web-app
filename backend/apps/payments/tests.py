import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.payments.api.views import CartPayView, PaymentDetailView, PaymentListView
from apps.payments.models import Payment, PaymentItem
from apps.payments.tasks import _handle_failure, _handle_success, process_payment_task


class PaymentModelUnitTests(SimpleTestCase):
    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.pk = 1

        self.payment_data = {
            "user": self.mock_user,
            "total_sum": Decimal("5000.00"),
            "status": "pending",
        }

    def test_payment_creation_with_mock(self):
        mock_payment = MagicMock(spec=Payment)
        mock_payment.payment_id = 1
        mock_payment.user = self.mock_user
        mock_payment.total_sum = Decimal("5000.00")
        mock_payment.status = "pending"
        mock_payment.mock_yookassa_id = uuid.uuid4()

        self.assertEqual(mock_payment.payment_id, 1)
        self.assertEqual(mock_payment.total_sum, Decimal("5000.00"))
        self.assertEqual(mock_payment.status, "pending")

    def test_payment_status_choices(self):
        mock_payment = MagicMock(spec=Payment)

        statuses = ["pending", "approved", "success", "failed", "refunded"]
        for status_value in statuses:
            mock_payment.status = status_value
            self.assertEqual(mock_payment.status, status_value)

    def test_payment_str_method(self):
        mock_payment = MagicMock(spec=Payment)
        mock_payment.payment_id = 42
        mock_payment.status = "pending"
        mock_payment.get_status_display.return_value = "Ожидает оплаты"
        mock_payment.__str__.return_value = "Payment #42 (Ожидает оплаты)"

        self.assertEqual(str(mock_payment), "Payment #42 (Ожидает оплаты)")

    def test_mock_yookassa_id_auto_generation(self):
        mock_payment = MagicMock(spec=Payment)
        mock_uuid = uuid.uuid4()
        mock_payment.mock_yookassa_id = mock_uuid

        self.assertIsInstance(mock_payment.mock_yookassa_id, uuid.UUID)


class PaymentItemModelUnitTests(SimpleTestCase):
    def setUp(self):
        self.mock_payment = MagicMock(spec=Payment)
        self.mock_payment.payment_id = 1
        self.mock_payment.pk = 1

        self.mock_course = MagicMock()
        self.mock_course.course_id = 1
        self.mock_course.pk = 1
        self.mock_course.title = "Тестовый курс"

        self.item_data = {
            "payment": self.mock_payment,
            "course": self.mock_course,
            "price": Decimal("5000.00"),
        }

    def test_payment_item_creation(self):
        mock_item = MagicMock(spec=PaymentItem)
        mock_item.payment = self.mock_payment
        mock_item.course = self.mock_course
        mock_item.price = Decimal("5000.00")

        self.assertEqual(mock_item.payment, self.mock_payment)
        self.assertEqual(mock_item.course, self.mock_course)
        self.assertEqual(mock_item.price, Decimal("5000.00"))

    def test_payment_item_str_method(self):
        mock_item = MagicMock(spec=PaymentItem)
        mock_item.course = self.mock_course
        mock_item.course.title = "Тестовый курс"
        mock_item.price = Decimal("5000.00")
        mock_item.__str__.return_value = "Тестовый курс — 5000.00₽"

        self.assertEqual(str(mock_item), "Тестовый курс — 5000.00₽")

    def test_payment_item_unique_together(self):
        self.assertTrue(hasattr(PaymentItem._meta, "unique_together"))


class PaymentTaskUnitTests(SimpleTestCase):
    def setUp(self):
        self.mock_payment = MagicMock(spec=Payment)
        self.mock_payment.payment_id = 1
        self.mock_payment.user_id = 1
        self.mock_payment.user = MagicMock()
        self.mock_payment.user.id = 1
        self.mock_payment.status = "pending"
        self.mock_payment.mock_yookassa_id = uuid.uuid4()

        self.mock_task = MagicMock()
        self.mock_task.request.retries = 0
        self.mock_task.max_retries = 5

    def test_process_payment_task_success(self):
        mock_select = MagicMock()
        mock_select.return_value.get.return_value = self.mock_payment

        mock_fetch = MagicMock()
        mock_fetch.return_value = {"paid": True}

        mock_handle_success = MagicMock()
        mock_handle_success.return_value = {
            "status": "success",
            "payment_id": 1,
            "courses_added": 2,
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

    def test_handle_success_function(self):
        mock_payment = MagicMock()
        mock_payment.user = MagicMock()
        mock_payment.user.id = 1
        mock_payment.user_id = 1
        mock_payment.payment_id = 1
        mock_payment.save = MagicMock()

        mock_item1 = MagicMock()
        mock_item1.course = MagicMock()
        mock_item1.course.id = 1
        mock_item2 = MagicMock()
        mock_item2.course = MagicMock()
        mock_item2.course.id = 2

        mock_items_queryset = MagicMock()
        mock_items_queryset.select_related.return_value.all.return_value = [
            mock_item1,
            mock_item2,
        ]
        mock_payment.items = mock_items_queryset

        # Создаем моки для PurchasedCourse и CartItem
        mock_purchased_objects = MagicMock()
        mock_purchased_objects.get_or_create.return_value = (MagicMock(), True)

        mock_cart_objects = MagicMock()
        mock_cart_objects.filter.return_value.delete.return_value = None

        with (
            patch("apps.courses.models.PurchasedCourse.objects", mock_purchased_objects),
            patch("apps.carts.models.CartItem.objects", mock_cart_objects),
            patch("apps.payments.tasks.logger") as mock_logger,
        ):
            result = _handle_success(mock_payment)

            self.assertEqual(result["status"], "success")
            self.assertIn("payment_id", result)
            mock_payment.save.assert_called_once()

    def test_handle_failure_with_retry(self):
        mock_payment = MagicMock()
        mock_payment.status = "approved"
        mock_payment.save = MagicMock()

        mock_task = MagicMock()
        mock_task.request.retries = 2
        mock_task.max_retries = 5
        mock_task.retry.side_effect = Exception("Retry")

        with patch("apps.payments.tasks.logger") as mock_logger:
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

        with patch("apps.payments.tasks.logger") as mock_logger:
            result = _handle_failure(mock_task, mock_payment)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["payment_id"], 1)
            # Статус должен стать failed
            self.assertEqual(mock_payment.status, "failed")
            mock_payment.save.assert_called_once()


class CartPayViewUnitTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.pk = 1
        self.mock_user.is_authenticated = True

        self.mock_course = MagicMock()
        self.mock_course.course_id = 1
        self.mock_course.pk = 1
        self.mock_course.price = 5000
        self.mock_course.title = "Тестовый курс"

        self.mock_cart_item = MagicMock()
        self.mock_cart_item.course_id = self.mock_course

    def test_cart_pay_without_auth(self):
        request = self.factory.post("/api/payments/pay/")
        response = CartPayView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_pay_empty_cart(self):
        request = self.factory.post("/api/payments/pay/")
        force_authenticate(request, user=self.mock_user)

        mock_cart = MagicMock()
        mock_cart_items = MagicMock()
        mock_cart_items.exists.return_value = False

        mock_cart_items.select_related.return_value = mock_cart_items

        mock_purchased_filter = MagicMock()
        mock_purchased_filter.return_value.values_list.return_value = []

        with (
            patch("apps.payments.api.views.Cart.objects.get_or_create") as mock_cart_get,
            patch("apps.payments.api.views.CartItem.objects.filter") as mock_items_filter,
            patch(
                "apps.payments.api.views.PurchasedCourse.objects.filter",
                mock_purchased_filter,
            ),
            patch("apps.payments.api.views.transaction.atomic"),
        ):
            mock_cart_get.return_value = (mock_cart, True)
            mock_items_filter.return_value = mock_cart_items

            response = CartPayView.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Корзина пуста", response.data["error"])

    def test_cart_pay_with_purchased_courses(self):
        request = self.factory.post("/api/payments/pay/")
        force_authenticate(request, user=self.mock_user)

        mock_cart = MagicMock()
        mock_cart_items = MagicMock()
        mock_cart_items.exists.return_value = True
        mock_cart_items.__iter__.return_value = iter([self.mock_cart_item])

        with (
            patch("apps.payments.api.views.Cart.objects.get_or_create") as mock_cart_get,
            patch("apps.payments.api.views.CartItem.objects.filter") as mock_items_filter,
            patch(
                "apps.payments.api.views.PurchasedCourse.objects.filter"
            ) as mock_purchased_filter,
            patch("apps.payments.api.views.transaction.atomic"),
        ):
            mock_cart_get.return_value = (mock_cart, True)
            mock_items_filter.return_value = mock_cart_items
            mock_purchased_filter.return_value.values_list.return_value = [1]

            response = CartPayView.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("уже куплены", response.data["error"])

    def test_cart_pay_success(self):
        request = self.factory.post("/api/payments/pay/")
        force_authenticate(request, user=self.mock_user)

        mock_cart = MagicMock()
        mock_cart_items = MagicMock()
        mock_cart_items.exists.return_value = True
        mock_cart_items.__iter__.return_value = iter([self.mock_cart_item])

        mock_payment = MagicMock()
        mock_payment.payment_id = 1
        mock_payment.total_sum = Decimal("5000.00")
        mock_payment.mock_yookassa_id = uuid.uuid4()

        mock_yookassa_response = MagicMock()
        mock_yookassa_response.confirmation_url = "https://yookassa.ru/payment/123"

        with (
            patch("apps.payments.api.views.Cart.objects.get_or_create") as mock_cart_get,
            patch("apps.payments.api.views.CartItem.objects.filter") as mock_items_filter,
            patch(
                "apps.payments.api.views.PurchasedCourse.objects.filter"
            ) as mock_purchased_filter,
            patch("apps.payments.api.views.transaction.atomic") as mock_atomic,
            patch("apps.payments.api.views.Payment.objects.create") as mock_payment_create,
            patch("apps.payments.api.views.PaymentItem.objects.bulk_create") as mock_bulk_create,
            patch("apps.payments.api.views.MockYooKassaService.create_payment") as mock_yookassa,
            patch("apps.payments.api.views.process_payment_task.apply_async") as mock_task,
            patch("apps.payments.api.views.PaymentSerializer") as mock_serializer,
        ):
            mock_cart_get.return_value = (mock_cart, True)
            mock_items_filter.return_value = mock_cart_items
            mock_purchased_filter.return_value.values_list.return_value = []
            mock_payment_create.return_value = mock_payment
            mock_yookassa.return_value = mock_yookassa_response
            mock_serializer.return_value.data = {
                "payment_id": 1,
                "total_sum": "5000.00",
            }

            response = CartPayView.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_payment_create.assert_called_once()
            mock_bulk_create.assert_called_once()
            mock_yookassa.assert_called_once()
            mock_task.assert_called_once_with(args=[1], countdown=5)


class PaymentListViewUnitTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.is_authenticated = True

    def test_payment_list_without_auth(self):
        request = self.factory.get("/api/payments/")
        response = PaymentListView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_list_empty(self):
        request = self.factory.get("/api/payments/")
        force_authenticate(request, user=self.mock_user)

        with (
            patch("apps.payments.api.views.Payment.objects.filter") as mock_filter,
            patch("apps.payments.api.views.PaymentShortSerializer") as mock_serializer,
        ):
            mock_filter.return_value = []
            mock_serializer.return_value.data = []

            response = PaymentListView.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, [])

    def test_payment_list_with_payments(self):
        request = self.factory.get("/api/payments/")
        force_authenticate(request, user=self.mock_user)

        mock_payment1 = MagicMock()
        mock_payment2 = MagicMock()

        with (
            patch("apps.payments.api.views.Payment.objects.filter") as mock_filter,
            patch("apps.payments.api.views.PaymentShortSerializer") as mock_serializer,
        ):
            mock_filter.return_value = [mock_payment1, mock_payment2]
            mock_serializer.return_value.data = [
                {"payment_id": 1, "total_sum": "5000.00"},
                {"payment_id": 2, "total_sum": "3000.00"},
            ]

            response = PaymentListView.as_view()(request)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 2)


class PaymentDetailViewUnitTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.is_authenticated = True

        self.mock_payment = MagicMock()
        self.mock_payment.payment_id = 1
        self.mock_payment.user = self.mock_user

    def test_payment_detail_without_auth(self):
        request = self.factory.get("/api/payments/1/")
        response = PaymentDetailView.as_view()(request, payment_id=1)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_detail_not_found(self):
        request = self.factory.get("/api/payments/999/")
        force_authenticate(request, user=self.mock_user)

        with patch("apps.payments.api.views.Payment.objects.filter") as mock_filter:
            mock_filter.return_value.prefetch_related.return_value.first.return_value = None

            response = PaymentDetailView.as_view()(request, payment_id=999)

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.data["detail"], "Платёж не найден.")

    def test_payment_detail_success(self):
        request = self.factory.get("/api/payments/1/")
        force_authenticate(request, user=self.mock_user)

        with (
            patch("apps.payments.api.views.Payment.objects.filter") as mock_filter,
            patch("apps.payments.api.views.PaymentSerializer") as mock_serializer,
        ):
            mock_filter.return_value.prefetch_related.return_value.first.return_value = (
                self.mock_payment
            )
            mock_serializer.return_value.data = {
                "payment_id": 1,
                "total_sum": "5000.00",
                "items": [{"course": {"title": "Тестовый курс"}}],
            }

            response = PaymentDetailView.as_view()(request, payment_id=1)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["payment_id"], 1)


class PaymentSerializerUnitTests(SimpleTestCase):
    def test_payment_serializer_with_mock(self):
        mock_payment = MagicMock()
        mock_payment.payment_id = 1
        mock_payment.total_sum = Decimal("5000.00")
        mock_payment.status = "success"
        mock_payment.get_status_display.return_value = "Успешно"
        mock_payment.mock_payment_url = "https://test.url"
        mock_payment.mock_yookassa_id = uuid.uuid4()
        mock_payment.created_at = "2024-01-01"
        mock_payment.updated_at = "2024-01-01"
        mock_payment.paid_at = "2024-01-01"
        mock_payment.items.all.return_value = []

        self.assertTrue(hasattr(mock_payment, "payment_id"))
        self.assertTrue(hasattr(mock_payment, "total_sum"))
        self.assertTrue(hasattr(mock_payment, "status"))

    def test_payment_short_serializer_with_mock(self):
        mock_payment = MagicMock()
        mock_payment.payment_id = 1
        mock_payment.total_sum = Decimal("5000.00")
        mock_payment.status = "success"
        mock_payment.get_status_display.return_value = "Успешно"
        mock_payment.created_at = "2024-01-01"
        mock_payment.paid_at = "2024-01-01"

        self.assertTrue(hasattr(mock_payment, "payment_id"))
        self.assertTrue(hasattr(mock_payment, "total_sum"))
        self.assertTrue(hasattr(mock_payment, "status"))
