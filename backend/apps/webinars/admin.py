from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Recording, Webinar


class RecordingInline(TabularInline):
    model = Recording
    extra = 0
    can_delete = False
    readonly_fields = (
        "recording_id",
        "status_badge",
        "kinescope_upload_badge",
        "duration_display",
        "started_at",
        "ended_at",
        "recording_url",
    )
    fields = readonly_fields
    show_change_link = True

    def status_badge(self, obj):
        colors = {
            "recording": "blue",
            "processing": "yellow",
            "ready": "green",
            "failed": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="padding:2px 8px;border-radius:4px;font-size:11px;background:var(--color-{}-100,#e5e7eb);color:var(--color-{}-700,#374151)">{}</span>',
            color,
            color,
            obj.get_status_display(),
        )

    def kinescope_upload_badge(self, obj):
        colors = {
            "none": "gray",
            "pending": "yellow",
            "uploading": "blue",
            "processing": "yellow",
            "ready": "green",
            "failed": "red",
        }
        color = colors.get(obj.kinescope_upload_status, "gray")
        return format_html(
            '<span style="padding:2px 8px;border-radius:4px;font-size:11px;background:var(--color-{}-100,#e5e7eb);color:var(--color-{}-700,#374151)">{}</span>',
            color,
            color,
            obj.get_kinescope_upload_status_display(),
        )

    def duration_display(self, obj):
        if obj.duration_seconds:
            m, s = divmod(obj.duration_seconds, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        return "—"

    status_badge.short_description = "Статус"
    kinescope_upload_badge.short_description = "Kinescope"
    duration_display.short_description = "Длительность"


@admin.register(Webinar)
class WebinarAdmin(ModelAdmin):
    list_display = (
        "lesson_link",
        "status_badge",
        "started_by_link",
        "scheduled_at",
        "started_at",
        "ended_at",
        "recordings_count",
    )
    list_filter = ("status", "created_at")
    search_fields = ("lesson__title", "lesson__section__course__title", "agora_channel_name")
    readonly_fields = (
        "webinar_id",
        "agora_channel_name",
        "whiteboard_room_uuid",
        "started_at",
        "ended_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
    inlines = [RecordingInline]

    fieldsets = (
        (
            "Основное",
            {
                "fields": ("webinar_id", "lesson", "status", "started_by"),
            },
        ),
        (
            "Расписание",
            {
                "fields": ("scheduled_at", "started_at", "ended_at"),
            },
        ),
        (
            "Интеграции",
            {
                "fields": ("agora_channel_name", "whiteboard_room_uuid"),
                "classes": ["collapse"],
            },
        ),
        (
            "Даты создания",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="Урок")
    def lesson_link(self, obj):
        url = reverse("admin:courses_lesson_change", args=[obj.lesson_id])
        return format_html('<a href="{}">{}</a>', url, obj.lesson.title)

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {
            "pending": "yellow",
            "live": "green",
            "ended": "gray",
        }
        return obj.get_status_display(), colors.get(obj.status, "gray")

    @display(description="Запустил")
    def started_by_link(self, obj):
        if obj.started_by:
            url = reverse("admin:users_user_change", args=[obj.started_by_id])
            name = f"{obj.started_by.first_name} {obj.started_by.last_name}".strip() or str(
                obj.started_by
            )
            return format_html('<a href="{}">{}</a>', url, name)
        return "—"

    @display(description="Записей")
    def recordings_count(self, obj):
        return obj.recordings.filter(is_deleted=False).count()


@admin.register(Recording)
class RecordingAdmin(ModelAdmin):
    list_display = (
        "recording_short_id",
        "webinar_link",
        "status_badge",
        "kinescope_badge",
        "duration_display",
        "started_at",
        "is_deleted",
    )
    list_filter = ("status", "kinescope_upload_status", "is_deleted")
    search_fields = ("recording_id", "kinescope_video_id", "webinar__lesson__title")
    readonly_fields = (
        "recording_id",
        "webinar",
        "started_by",
        "status",
        "resource_id",
        "sid",
        "recording_url",
        "kinescope_video_id",
        "kinescope_upload_status",
        "whiteboard_pdf_url",
        "started_at",
        "ended_at",
        "is_deleted",
        "deleted_at",
        "deleted_by",
        "created_at",
        "updated_at",
    )
    actions = ["retry_kinescope_upload"]
    ordering = ("-started_at",)

    fieldsets = (
        (
            "Запись",
            {
                "fields": ("recording_id", "webinar", "started_by", "status"),
            },
        ),
        (
            "Ссылки",
            {
                "fields": ("recording_url", "whiteboard_pdf_url"),
            },
        ),
        (
            "Kinescope",
            {
                "fields": ("kinescope_video_id", "kinescope_upload_status"),
            },
        ),
        (
            "Время",
            {
                "fields": ("started_at", "ended_at"),
            },
        ),
        (
            "Удаление",
            {
                "fields": ("is_deleted", "deleted_at", "deleted_by"),
                "classes": ["collapse"],
            },
        ),
        (
            "Технические поля",
            {
                "fields": ("resource_id", "sid", "created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )

    @display(description="ID")
    def recording_short_id(self, obj):
        return str(obj.recording_id)[:8] + "…"

    @display(description="Вебинар")
    def webinar_link(self, obj):
        url = reverse("admin:webinars_webinar_change", args=[obj.webinar_id])
        return format_html('<a href="{}">{}</a>', url, obj.webinar.lesson.title)

    @display(description="Статус", label=True)
    def status_badge(self, obj):
        colors = {
            "recording": "blue",
            "processing": "yellow",
            "ready": "green",
            "failed": "red",
        }
        return obj.get_status_display(), colors.get(obj.status, "gray")

    @display(description="Kinescope", label=True)
    def kinescope_badge(self, obj):
        colors = {
            "none": "gray",
            "pending": "yellow",
            "uploading": "blue",
            "processing": "yellow",
            "ready": "green",
            "failed": "red",
        }
        return obj.get_kinescope_upload_status_display(), colors.get(
            obj.kinescope_upload_status, "gray"
        )

    @display(description="Длительность")
    def duration_display(self, obj):
        if obj.duration_seconds:
            m, s = divmod(obj.duration_seconds, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        return "—"

    def retry_kinescope_upload(self, request, queryset):
        from .tasks import upload_recording_to_kinescope

        count = 0
        for rec in queryset:
            if rec.recording_url:
                rec.kinescope_upload_status = "pending"
                rec.save(update_fields=["kinescope_upload_status", "updated_at"])
                upload_recording_to_kinescope.delay(str(rec.recording_id))
                count += 1
        self.message_user(request, f"Запущено повторных загрузок: {count}")

    retry_kinescope_upload.short_description = "Повторить загрузку в Kinescope"
