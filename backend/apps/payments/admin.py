from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Payment, PaymentItem


class PaymentItemInline(TabularInline):
    model = PaymentItem
    extra = 0
    readonly_fields = ("course_link", "price")
    fields = ("course_link", "price")

    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    course_link.short_description = "Курс"


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        "payment_id",
        "user_link",
        "total_sum_display",
        "status_badge",
        "created_at",
        "paid_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("user__email_cipher", "user__first_name", "mock_yookassa_id")
    readonly_fields = ("mock_yookassa_id", "created_at", "updated_at", "payment_id")
    ordering = ("-created_at",)
    inlines = [PaymentItemInline]

    fieldsets = (
        (
            "Основное",
            {
                "fields": ("payment_id", "user", "total_sum", "status"),
            },
        ),
        (
            "Платёжный шлюз",
            {
                "fields": ("mock_yookassa_id", "mock_payment_url"),
                "classes": ["collapse"],
            },
        ),
        (
            "Даты",
            {
                "fields": ("created_at", "updated_at", "paid_at"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="Пользователь")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    @display(description="Сумма")
    def total_sum_display(self, obj):
        return f"{obj.total_sum:,.2f} ₽"

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {
            "success": "green",
            "pending": "yellow",
            "approved": "blue",
            "failed": "red",
            "refunded": "orange",
        }
        return obj.get_status_display(), colors.get(obj.status, "gray")
