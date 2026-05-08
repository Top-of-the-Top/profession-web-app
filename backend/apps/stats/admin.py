from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import LessonProgress, RecordingView, WebinarAttendance


@admin.register(WebinarAttendance)
class WebinarAttendanceAdmin(ModelAdmin):
    list_display = (
        "user_link",
        "webinar_link",
        "joined_at",
        "left_at",
        "duration_display",
    )
    list_filter = ("webinar",)
    search_fields = ("user__email_cipher", "user__first_name", "webinar__lesson__title")
    readonly_fields = ("attendance_id", "created_at", "updated_at")
    raw_id_fields = ("user", "webinar")
    ordering = ("-joined_at",)

    @display(description="Студент")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        name = f"{obj.user.first_name} {obj.user.last_name}".strip() or str(obj.user)
        return format_html('<a href="{}">{}</a>', url, name)

    @display(description="Вебинар")
    def webinar_link(self, obj):
        url = reverse("admin:webinars_webinar_change", args=[obj.webinar_id])
        return format_html('<a href="{}">{}</a>', url, obj.webinar.lesson.title)

    @display(description="Просмотрено")
    def duration_display(self, obj):
        if obj.watched_seconds:
            m, s = divmod(obj.watched_seconds, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        return "—"


@admin.register(RecordingView)
class RecordingViewAdmin(ModelAdmin):
    list_display = (
        "user_link",
        "recording_link",
        "duration_display",
        "last_position_display",
        "updated_at",
    )
    list_filter = ("recording__webinar",)
    search_fields = ("user__email_cipher", "user__first_name", "recording__webinar__lesson__title")
    readonly_fields = ("view_id", "created_at", "updated_at")
    raw_id_fields = ("user", "recording")
    ordering = ("-updated_at",)

    @display(description="Студент")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        name = f"{obj.user.first_name} {obj.user.last_name}".strip() or str(obj.user)
        return format_html('<a href="{}">{}</a>', url, name)

    @display(description="Запись")
    def recording_link(self, obj):
        url = reverse("admin:webinars_recording_change", args=[obj.recording_id])
        return format_html('<a href="{}">…{}</a>', url, str(obj.recording_id)[:8])

    @display(description="Просмотрено")
    def duration_display(self, obj):
        if obj.watched_seconds:
            m, s = divmod(obj.watched_seconds, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        return "—"

    @display(description="Позиция")
    def last_position_display(self, obj):
        if obj.last_position:
            m, s = divmod(obj.last_position, 60)
            return f"{m:02d}:{s:02d}"
        return "—"


@admin.register(LessonProgress)
class LessonProgressAdmin(ModelAdmin):
    list_display = (
        "user_link",
        "lesson_link",
        "progress_bar",
        "all_homeworks_submitted",
        "is_completed_badge",
        "completed_at",
    )
    list_filter = ("is_completed", "all_homeworks_submitted")
    search_fields = (
        "user__email_cipher",
        "user__first_name",
        "lesson__title",
        "lesson__section__course__title",
    )
    readonly_fields = ("progress_id", "created_at", "updated_at", "completed_at")
    raw_id_fields = ("user", "lesson")
    ordering = ("-updated_at",)

    @display(description="Студент")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        name = f"{obj.user.first_name} {obj.user.last_name}".strip() or str(obj.user)
        return format_html('<a href="{}">{}</a>', url, name)

    @display(description="Урок")
    def lesson_link(self, obj):
        url = reverse("admin:courses_lesson_change", args=[obj.lesson_id])
        return format_html('<a href="{}">{}</a>', url, obj.lesson.title)

    @display(description="Просмотр")
    def progress_bar(self, obj):
        pct = int(obj.watched_ratio * 100)
        color = "#22c55e" if pct >= 80 else "#0ea5e9" if pct >= 40 else "#f59e0b"
        return format_html(
            '<div style="width:80px;background:#e5e7eb;border-radius:4px;overflow:hidden;">'
            '<div style="width:{}%;height:8px;background:{};"></div></div>'
            '<span style="font-size:11px;color:#6b7280;margin-left:4px;">{}%</span>',
            pct,
            color,
            pct,
        )

    @display(description="Завершён", boolean=True)
    def is_completed_badge(self, obj):
        return obj.is_completed
