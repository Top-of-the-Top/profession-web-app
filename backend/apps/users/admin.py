from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Profile, User


class ProfileInline(TabularInline):
    model = Profile
    extra = 0
    fields = ("birthday", "gender", "avatar_preview")
    readonly_fields = ("avatar_preview",)

    def avatar_preview(self, obj):
        if obj.avatar_url:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;border-radius:50%;object-fit:cover;" />',
                obj.avatar_url,
            )
        return "—"

    avatar_preview.short_description = "Аватар"


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "role_badge",
        "is_active_badge",
        "is_staff",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff", "date_joined")
    search_fields = ("email_cipher", "phone_cipher", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")
    inlines = [ProfileInline]

    fieldsets = (
        (
            "Идентификация",
            {
                "fields": ("email_cipher", "phone_cipher", "password"),
            },
        ),
        (
            "Личные данные",
            {
                "fields": ("first_name", "last_name", "role"),
            },
        ),
        (
            "Права доступа",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "classes": ["collapse"],
            },
        ),
        (
            "Даты",
            {
                "fields": ("date_joined", "last_login"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="Пользователь")
    def display_name(self, obj):
        full = f"{obj.first_name} {obj.last_name}".strip()
        if full:
            return full
        if obj.email_cipher:
            return obj.email_cipher[:30] + ("..." if len(obj.email_cipher) > 30 else "")
        return f"User #{obj.id}"

    @display(description="Роль", label=True)
    def role_badge(self, obj):
        colors = {
            "student": "blue",
            "teacher": "green",
            "moderator": "orange",
        }
        return obj.get_role_display(), colors.get(obj.role, "gray")

    @display(description="Активен", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ("profile_id", "user_link", "gender", "birthday", "avatar_preview")
    search_fields = (
        "user__email_cipher",
        "user__phone_cipher",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = ("avatar_preview",)

    @display(description="Пользователь")
    def user_link(self, obj):
        from django.urls import reverse

        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    @display(description="Аватар")
    def avatar_preview(self, obj):
        if obj.avatar_url:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;border-radius:50%;object-fit:cover;" />',
                obj.avatar_url,
            )
        return "—"
