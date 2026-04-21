from django.contrib import admin

from .models import Attachment, AssetUsage, MediaAsset


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('attachment_id', 'name', 'size', 'file_extension', 'uploader', 'created_at')
    search_fields = ('name', 'url')
    list_filter = ('file_extension', 'created_at')
    readonly_fields = ('attachment_id', 'created_at')


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = (
        'asset_id',
        'storage_backend',
        'status',
        'visibility',
        'original_filename',
        'size_bytes',
        'ref_count',
        'owner',
        'created_at',
    )
    list_filter = (
        'status',
        'storage_backend',
        'visibility',
        'created_at',
    )
    search_fields = (
        'asset_id',
        'storage_key',
        'original_filename',
        'checksum_sha256',
        'owner__username',
        'owner__email',
    )
    readonly_fields = (
        'asset_id',
        'ref_count',
        'created_at',
        'committed_at',
        'deleted_at',
        'unreferenced_since',
        'checksum_sha256',
        'size_bytes',
    )
    fieldsets = (
        ('Идентификация', {
            'fields': ('asset_id', 'storage_backend', 'storage_key'),
        }),
        ('Содержимое', {
            'fields': (
                'original_filename',
                'mime_type',
                'size_bytes',
                'checksum_sha256',
            ),
        }),
        ('Жизненный цикл', {
            'fields': (
                'status',
                'visibility',
                'ref_count',
                'unreferenced_since',
                'owner',
                'created_at',
                'committed_at',
                'deleted_at',
            ),
        }),
    )


@admin.register(AssetUsage)
class AssetUsageAdmin(admin.ModelAdmin):
    list_display = ('usage_id', 'asset', 'role', 'content_type', 'object_id', 'created_at')
    list_filter = ('role', 'content_type', 'created_at')
    search_fields = ('asset__asset_id', 'object_id')
    readonly_fields = ('usage_id', 'created_at')
    raw_id_fields = ('asset',)
