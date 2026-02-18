from decimal import Decimal
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from ..models import Payment, PaymentItem
from ...courses.models import PurchasedCourse
from ..services import MockYooKassaService
from ..tasks import process_payment_task
from ...cart.models import Cart, CartItem

from .serializers import (
    PaymentSerializer,
    PaymentShortSerializer,
)


class CartPayView(APIView):
    """
    POST /api/cart/pay/

    Создаёт платёж из текущей корзины пользователя.
    Курсы из корзины фиксируются в PaymentItem.
    Оплата обрабатывается асинхронно через Celery.
    Возвращает объект Payment с mock_payment_url для редиректа на оплату.
    """
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Оплатить корзину',
        description=(
            'Создаёт платёж на основе текущей корзины. '
            'Возвращает URL для оплаты (мок ЮKassa). '
            'Статус платежа обновляется асинхронно.'
        ),
        responses={
            201: PaymentSerializer,
            400: {
                'description': 'Корзина пуста.',
            },
        },
    )
    
    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(
            cart_id=cart,
        ).select_related('course_id')

        if not cart_items.exists():
            return Response(
                {'error': 'Корзина пуста. Добавьте курсы перед оплатой.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_purchased = PurchasedCourse.objects.filter(
            user=request.user,
            course__in=[item.course_id for item in cart_items],
        ).values_list('course_id', flat=True)

        if already_purchased:
            return Response(
                {'error': 'Некоторые курсы уже куплены.', 'course_ids': list(already_purchased)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            total_sum = sum(
                Decimal(item.course_id.price) for item in cart_items
            )

            payment = Payment.objects.create(
                user=request.user,
                total_sum=total_sum,
            )

            payment_items = [
                PaymentItem(
                    payment=payment,
                    course=item.course_id,
                    price=Decimal(item.course_id.price),
                )
                for item in cart_items
            ]
            PaymentItem.objects.bulk_create(payment_items)

        yookassa_response = MockYooKassaService.create_payment(
            amount=payment.total_sum,
            description=f'Оплата заказа #{payment.payment_id}',
            idempotency_key=str(payment.mock_yookassa_id),
        )

        payment.mock_payment_url = yookassa_response.confirmation_url
        payment.save(update_fields=['mock_payment_url', 'updated_at'])

        process_payment_task.apply_async(
            args=[payment.payment_id],
            countdown=5,
        )

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaymentListView(APIView):
    """
    GET /api/payments/

    Список всех платежей текущего пользователя.
    """
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Список платежей',
        description='Возвращает все платежи текущего пользователя.',
        responses={200: PaymentShortSerializer(many=True)},
    )
    def get(self, request):
        payments = Payment.objects.filter(user=request.user)
        serializer = PaymentShortSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentDetailView(APIView):
    """
    GET /api/payments/<payment_id>/

    Детальная информация о платеже с позициями.
    """
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary='Детали платежа',
        description='Возвращает подробную информацию о платеже с перечнем курсов.',
        responses={
            200: PaymentSerializer,
            404: {'description': 'Платёж не найден.'},
        },
    )
    def get(self, request, payment_id):
        payment = Payment.objects.filter(
            payment_id=payment_id,
            user=request.user,
        ).prefetch_related('items__course').first()

        if payment is None:
            return Response(
                {'detail': 'Платёж не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)


