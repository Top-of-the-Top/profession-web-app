from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(ModelAdmin):
    list_display = (
        "email",
        "status_badge",
        "invited_by_link",
        "created_at",
        "expires_at",
        "used_at",
    )
    list_filter = ("created_at", "expires_at")
    search_fields = ("email", "invited_by__email_cipher", "invited_by__first_name")
    readonly_fields = ("invitation_id", "token", "created_at", "expires_at", "used_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Приглашение",
            {
                "fields": ("invitation_id", "email", "invited_by"),
            },
        ),
        (
            "Токен и сроки",
            {
                "fields": ("token", "created_at", "expires_at", "used_at"),
            },
        ),
    )

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        status = obj.status
        colors = {
            "used": "green",
            "expired": "red",
            "pending": "yellow",
        }
        labels = {
            "used": "Использовано",
            "expired": "Истекло",
            "pending": "Ожидает",
        }
        return labels.get(status, status), colors.get(status, "gray")

    @display(description="Кто пригласил")
    def invited_by_link(self, obj):
        if obj.invited_by:
            url = reverse("admin:users_user_change", args=[obj.invited_by_id])
            name = f"{obj.invited_by.first_name} {obj.invited_by.last_name}".strip() or str(
                obj.invited_by
            )
            return format_html('<a href="{}">{}</a>', url, name)
        return "—"
