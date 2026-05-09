from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "title",
        "type_badge",
        "user_link",
        "course_link",
        "read_count",
        "created_at",
    )
    list_filter = ("notification_type", "created_at")
    search_fields = ("title", "message", "user__email_cipher", "course__title")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Уведомление",
            {
                "fields": ("notification_type", "title", "message"),
            },
        ),
        (
            "Адресат",
            {
                "fields": ("user", "course"),
            },
        ),
        (
            "Прочитано",
            {
                "fields": ("read_by",),
                "classes": ["collapse"],
            },
        ),
        (
            "Дата",
            {
                "fields": ("created_at",),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="Тип", label=True)
    def type_badge(self, obj):
        colors = {
            "personal": "blue",
            "course": "green",
            "system": "orange",
        }
        return obj.get_notification_type_display(), colors.get(obj.notification_type, "gray")

    @display(description="Пользователь")
    def user_link(self, obj):
        if obj.user:
            url = reverse("admin:users_user_change", args=[obj.user_id])
            return format_html('<a href="{}">{}</a>', url, obj.user)
        return "—"

    @display(description="Курс")
    def course_link(self, obj):
        if obj.course:
            url = reverse("admin:courses_course_change", args=[obj.course_id])
            return format_html('<a href="{}">{}</a>', url, obj.course.title)
        return "—"

    @display(description="Прочитали")
    def read_count(self, obj):
        return obj.read_by.count()
