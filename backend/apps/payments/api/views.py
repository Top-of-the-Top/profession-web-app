from decimal import Decimal

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...carts.models import Cart, CartItem
from ...courses.models import PurchasedCourse
from ..models import Payment, PaymentItem
from ..services import MockYooKassaService
from ..tasks import process_payment_task
from .serializers import PaymentSerializer, PaymentShortSerializer

SCHEMA_401 = {
    "type": "object",
    "properties": {
        "detail": {"type": "string", "description": "Токен отсутствует или недействителен."}
    },
}
SCHEMA_404 = {
    "type": "object",
    "properties": {"detail": {"type": "string", "description": "Платёж не найден."}},
}
SCHEMA_400 = {
    "type": "object",
    "properties": {
        "error": {"type": "string"},
        "course_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Опционально при уже купленных курсах.",
        },
    },
}


class CartPayView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Оплатить корзину",
        description=(
            "Создаёт платёж на основе текущей корзины пользователя. Требуется Authorization: Bearer <access_token>. "
            "Корзина должна быть непустой; все курсы в корзине не должны быть уже куплены. "
            "При успехе создаётся платёж, возвращается полный объект платежа (payment_id, total_sum, status, mock_payment_url, items с курсами и ценами). "
            "Статус платежа обновляется асинхронно через Celery после создания. "
            "400: пустая корзина (error: «Корзина пуста...») или часть курсов уже куплена (error и course_ids). "
            "401: токен отсутствует или недействителен."
        ),
        tags=["Carts"],
        responses={
            204: None,
            400: {
                "description": "Тело: { error } или { error, course_ids }. Корзина пуста или курсы уже куплены.",
                "schema": SCHEMA_400,
            },
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(
            cart_id=cart,
        ).select_related("course")

        if not cart_items.exists():
            return Response(
                {"error": "Корзина пуста. Добавьте курсы перед оплатой."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_purchased = PurchasedCourse.objects.filter(
            user=request.user,
            course__in=[item.course_id for item in cart_items],
        ).values_list("course_id", flat=True)

        if already_purchased:
            return Response(
                {"error": "Некоторые курсы уже куплены.", "course_ids": list(already_purchased)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            from datetime import timedelta

            from django.utils import timezone

            from apps.courses.api.utils.cache_utils import purchased_courses_cache_key

            total_sum = sum(Decimal(item.course.price) for item in cart_items)

            payment = Payment.objects.create(
                user=request.user,
                total_sum=total_sum,
            )

            PaymentItem.objects.bulk_create(
                [
                    PaymentItem(
                        payment=payment,
                        course=item.course,
                        price=Decimal(item.course.price),
                    )
                    for item in cart_items
                ]
            )

            access_expires = timezone.now() + timedelta(days=365)
            PurchasedCourse.objects.bulk_create(
                [
                    PurchasedCourse(
                        user=request.user,
                        course=item.course,
                        payment=payment,
                        access_expires_at=access_expires,
                    )
                    for item in cart_items
                ],
                ignore_conflicts=True,
            )

            CartItem.objects.filter(cart_id=cart).delete()

        from django.core.cache import caches

        cache = caches["default"]
        cache.delete(purchased_courses_cache_key(request.user.id))
        caches["hot"].delete(f"hot:carts:cart:{request.user.id}")

        yookassa_response = MockYooKassaService.create_payment(
            amount=payment.total_sum,
            description=f"Оплата заказа #{payment.payment_id}",
            idempotency_key=str(payment.mock_yookassa_id),
        )

        payment.mock_payment_url = yookassa_response.confirmation_url
        payment.save(update_fields=["mock_payment_url", "updated_at"])

        process_payment_task.apply_async(
            args=[payment.payment_id],
            countdown=5,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Список платежей",
        description=(
            "Возвращает список всех платежей текущего пользователя (краткий формат). "
            "Требуется Authorization: Bearer <access_token>. "
            "Каждый элемент: payment_id, total_sum, status, status_display, created_at, paid_at. "
            "При невалидном токене — 401 с полем detail."
        ),
        tags=["Payments"],
        responses={
            200: PaymentShortSerializer(many=True),
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def get(self, request):
        payments = Payment.objects.filter(user=request.user)
        serializer = PaymentShortSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Детали платежа",
        description=(
            "Возвращает полную информацию о платеже по payment_id (в пути URL). Требуется Authorization: Bearer <access_token>. "
            "Доступ только к своим платежам; при запросе чужого или несуществующего — 404. "
            "В ответе: payment_id, total_sum, status, status_display, mock_payment_url, mock_yookassa_id, created_at, updated_at, paid_at, items (массив позиций: course, price). "
            "При невалидном токене — 401; при ненайденном/чужом платеже — 404 с полем detail: «Платёж не найден.»."
        ),
        tags=["Payments"],
        responses={
            200: PaymentSerializer,
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
            404: {
                "description": "Тело: { detail: 'Платёж не найден.' }. Чужие платежи тоже 404.",
                "schema": SCHEMA_404,
            },
        },
    )
    def get(self, request, payment_id):
        payment = (
            Payment.objects.filter(
                payment_id=payment_id,
                user=request.user,
            )
            .prefetch_related("items__course")
            .first()
        )

        if payment is None:
            return Response(
                {"detail": "Платёж не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
