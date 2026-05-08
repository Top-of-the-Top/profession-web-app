from django.contrib import admin

from .models import LessonProgress, RecordingView, WebinarAttendance


@admin.register(WebinarAttendance)
class WebinarAttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "webinar", "joined_at", "left_at", "watched_seconds")
    list_filter = ("webinar",)
    search_fields = ("user__email_cipher",)
    raw_id_fields = ("user", "webinar")


@admin.register(RecordingView)
class RecordingViewAdmin(admin.ModelAdmin):
    list_display = ("user", "recording", "watched_seconds", "last_position", "updated_at")
    list_filter = ("recording__webinar",)
    search_fields = ("user__email_cipher",)
    raw_id_fields = ("user", "recording")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "lesson",
        "watched_ratio",
        "all_homeworks_submitted",
        "is_completed",
        "completed_at",
    )
    list_filter = ("is_completed",)
    search_fields = ("user__email_cipher", "lesson__title")
    raw_id_fields = ("user", "lesson")
