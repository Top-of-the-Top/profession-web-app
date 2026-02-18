from django.db import models
from ..users.models import User
from ..courses.models import Course
import uuid


class Payment(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Ожидает оплаты'),
        ('approved', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    )

    payment_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    total_sum = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
    )

    mock_payment_url = models.URLField(null=True, blank=True)
    mock_yookassa_id = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment #{self.payment_id} ({self.get_status_display()})'


class PaymentItem(models.Model):
    """Снимок курсов из корзины на момент создания платежа."""

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='items',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'payment_items'
        verbose_name = 'Позиция платежа'
        verbose_name_plural = 'Позиции платежа'
        unique_together = ('payment', 'course')

    def __str__(self):
        return f'{self.course} — {self.price}₽'


