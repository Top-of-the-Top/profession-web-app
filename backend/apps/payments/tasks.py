import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    acks_late=True,
)
def process_payment_task(self, payment_id: int):

    from .models import Payment
    from .services import MockYooKassaService

    try:
        payment = Payment.objects.select_related('user').get(payment_id=payment_id)
    except Payment.DoesNotExist:
        logger.error('Payment %s не найден', payment_id)
        return {'status': 'error', 'detail': f'Payment {payment_id} not found'}

    if payment.status not in ('pending', 'approved'):
        logger.info('Payment %s уже обработан: %s', payment_id, payment.status)
        return {'status': 'skipped', 'detail': f'Already {payment.status}'}

    payment.status = 'approved'
    payment.save(update_fields=['status', 'updated_at'])

    yookassa_result = MockYooKassaService.fetch_payment_status(
        str(payment.mock_yookassa_id),
    )

    if yookassa_result['paid']:
        return _handle_success(payment)
    else:
        return _handle_failure(self, payment)


def _handle_success(payment):
    payment.status = 'success'
    payment.paid_at = timezone.now()
    payment.save(update_fields=['status', 'paid_at', 'updated_at'])

    logger.info('Payment %s успешен для пользователя %s', payment.payment_id, payment.user_id)

    return {'status': 'success', 'payment_id': payment.payment_id}


def _handle_failure(task_instance, payment):
    payment.status = 'failed'
    payment.save(update_fields=['status', 'updated_at'])

    logger.warning(
        'Payment %s не прошёл (попытка %d/%d)',
        payment.payment_id,
        task_instance.request.retries,
        task_instance.max_retries,
    )

    if task_instance.request.retries < task_instance.max_retries:
        payment.status = 'pending'
        payment.save(update_fields=['status', 'updated_at'])
        raise task_instance.retry()

    return {
        'status': 'failed',
        'payment_id': payment.payment_id,
    }
