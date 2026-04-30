from django.contrib import admin
from .models import Webinar, Recording


class RecordingInline(admin.TabularInline):
    model = Recording
    extra = 0
    can_delete = False
    readonly_fields = (
        'recording_id',
        'status',
        'started_at',
        'ended_at',
        'resource_id',
        'sid',
        'recording_url',
        'kinescope_video_id',
        'kinescope_upload_status',
        'whiteboard_pdf_url',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    fields = readonly_fields


@admin.register(Webinar)
class WebinarAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'status', 'started_by', 'started_at', 'ended_at')
    readonly_fields = ('agora_channel_name', 'whiteboard_room_uuid', 'started_at', 'ended_at')
    inlines = [RecordingInline]


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = (
        'recording_id',
        'webinar',
        'status',
        'kinescope_upload_status',
        'started_at',
        'ended_at',
        'is_deleted',
    )
    list_filter = ('status', 'kinescope_upload_status', 'is_deleted')
    search_fields = ('recording_id', 'kinescope_video_id', 'webinar__lesson__title')
    readonly_fields = (
        'recording_id', 'webinar', 'started_by', 'status',
        'resource_id', 'sid', 'recording_url',
        'kinescope_video_id', 'kinescope_upload_status',
        'whiteboard_pdf_url',
        'started_at', 'ended_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )

    actions = ['retry_kinescope_upload']

    def retry_kinescope_upload(self, request, queryset):
        from .tasks import upload_recording_to_kinescope
        count = 0
        for rec in queryset:
            if rec.recording_url:
                rec.kinescope_upload_status = 'pending'
                rec.save(update_fields=['kinescope_upload_status', 'updated_at'])
                upload_recording_to_kinescope.delay(str(rec.recording_id))
                count += 1
        self.message_user(request, f'Запущено повторных загрузок: {count}')
    retry_kinescope_upload.short_description = 'Повторить загрузку в Kinescope'
