from django.contrib import admin
from .models import Payment, PaymentItem


class PaymentItemInline(admin.TabularInline):
    model = PaymentItem
    extra = 0
    readonly_fields = ('course', 'price')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_id', 'user', 'total_sum',
        'status', 'created_at', 'paid_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__email_cipher', 'mock_yookassa_id')
    readonly_fields = ('mock_yookassa_id', 'created_at', 'updated_at')
    inlines = [PaymentItemInline]
