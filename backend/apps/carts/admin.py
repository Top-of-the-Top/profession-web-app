from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("course_link", "course_price")
    fields = ("course_link", "course_price")

    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    def course_price(self, obj):
        return f"{obj.course.price:,} ₽"

    course_link.short_description = "Курс"
    course_price.short_description = "Цена"


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("cart_id", "user_link", "items_count", "total_display", "updated_at")
    search_fields = ("user__email_cipher", "user__first_name", "user__last_name")
    readonly_fields = ("cart_id", "created_at", "updated_at")
    ordering = ("-updated_at",)
    inlines = [CartItemInline]

    fieldsets = (
        (
            "Корзина",
            {
                "fields": ("cart_id", "user"),
            },
        ),
        (
            "Даты",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="Пользователь")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    @display(description="Товаров")
    def items_count(self, obj):
        return obj.courses.count()

    @display(description="Итого")
    def total_display(self, obj):
        total = sum(c.price for c in obj.courses.all())
        return f"{total:,} ₽" if total else "—"


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ("id", "cart_link", "course_link", "course_price")
    search_fields = ("cart__user__email_cipher", "course__title")
    readonly_fields = ("cart", "course")

    @display(description="Корзина")
    def cart_link(self, obj):
        url = reverse("admin:carts_cart_change", args=[obj.cart_id])
        return format_html('<a href="{}">Корзина #{}</a>', url, obj.cart_id)

    @display(description="Курс")
    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    @display(description="Цена")
    def course_price(self, obj):
        return f"{obj.course.price:,} ₽"
