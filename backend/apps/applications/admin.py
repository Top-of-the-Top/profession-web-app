from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import CourseApplication


@admin.register(CourseApplication)
class CourseApplicationAdmin(ModelAdmin):
    list_display = (
        "user_link",
        "course_link",
        "status_badge",
        "created_at",
        "reviewed_at",
        "reviewed_by_link",
    )
    list_filter = ("status", "created_at", "course")
    search_fields = ("user__email_cipher", "user__first_name", "course__title")
    readonly_fields = (
        "application_id",
        "user",
        "course",
        "status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    @display(description="Студент")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    @display(description="Курс")
    def course_link(self, obj):
        url = reverse("admin:courses_course_change", args=[obj.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.title)

    @display(description="Проверил")
    def reviewed_by_link(self, obj):
        if not obj.reviewed_by_id:
            return "—"
        url = reverse("admin:users_user_change", args=[obj.reviewed_by_id])
        return format_html('<a href="{}">{}</a>', url, obj.reviewed_by)

    @display(description="Статус")
    def status_badge(self, obj):
        colours = {
            CourseApplication.PENDING: "#f59e0b",
            CourseApplication.APPROVED: "#10b981",
            CourseApplication.REJECTED: "#ef4444",
        }
        colour = colours.get(obj.status, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            colour,
            obj.get_status_display(),
        )
