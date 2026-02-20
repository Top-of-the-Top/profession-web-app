import uuid
import random
import logging
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class YooKassaPaymentResponse:
    id: str
    status: str
    paid: bool
    amount_value: str
    amount_currency: str
    confirmation_url: str
    description: str


class MockYooKassaService: # Это мок-реализация платёжного шлюза ЮKassa.
    

    MOCK_BASE_URL = 'https://mock-yookassa.ru/payments'
    SUCCESS_PROBABILITY = 0.8 # Это вероятность успешного платежа.

    @classmethod
    def create_payment( # Это метод для создания платежа в (мок) ЮKassa.
        cls,
        amount: Decimal,
        currency: str = 'RUB',
        description: str = '',
        return_url: str = '',
        idempotency_key: Optional[str] = None,
    ) -> YooKassaPaymentResponse:
        
        payment_uuid = idempotency_key or str(uuid.uuid4())
        confirmation_url = f'{cls.MOCK_BASE_URL}/{payment_uuid}'

        logger.info(
            'MockYooKassa: создан платёж %s на сумму %s %s',
            payment_uuid, amount, currency,
        )

        return YooKassaPaymentResponse(
            id=payment_uuid,
            status='pending',
            paid=False,
            amount_value=str(amount),
            amount_currency=currency,
            confirmation_url=confirmation_url,
            description=description,
        )

    @classmethod
    def fetch_payment_status(cls, yookassa_id: str) -> dict: # Это метод - заглушка для проверки статуса платежа
        is_success = random.random() < cls.SUCCESS_PROBABILITY
        status = 'succeeded' if is_success else 'canceled'

        logger.info(
            'MockYooKassa: статус платежа %s → %s',
            yookassa_id, status,
        )

        return {
            'id': yookassa_id,
            'status': status,
            'paid': is_success,
        }

    @classmethod
    def capture_payment(cls, yookassa_id: str) -> dict: # Это метод - заглушка для подтверждения платежа.
        logger.info('MockYooKassa: capture платежа %s', yookassa_id)
        return {
            'id': yookassa_id,
            'status': 'succeeded',
            'paid': True,
        }

    @classmethod
    def refund_payment(cls, yookassa_id: str, amount: Decimal) -> dict: # Это метод - заглушка для возврата платежа.
        refund_id = str(uuid.uuid4())
        logger.info(
            'MockYooKassa: возврат %s на сумму %s',
            yookassa_id, amount,
        )
        return {
            'id': refund_id,
            'payment_id': yookassa_id,
            'status': 'succeeded',
            'amount': {'value': str(amount), 'currency': 'RUB'},
        }
