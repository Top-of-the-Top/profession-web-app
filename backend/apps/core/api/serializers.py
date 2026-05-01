from rest_framework import serializers

from ..meta_management.policies import INTENT_POLICIES


INTENT_CHOICES = tuple(INTENT_POLICIES.keys())


class InitiateUploadRequestSerializer(serializers.Serializer):
    intent = serializers.ChoiceField(choices=INTENT_CHOICES)
    filename = serializers.CharField(max_length=512)
    mime_type = serializers.CharField(max_length=128)
    size = serializers.IntegerField(min_value=1)


class PresignedUploadSerializer(serializers.Serializer):
    method = serializers.CharField()
    url = serializers.URLField()
    storage_key = serializers.CharField()
    expires_at = serializers.DateTimeField()
    fields = serializers.DictField(child=serializers.CharField(), default=dict)
    headers = serializers.DictField(child=serializers.CharField(), default=dict)


class InitiateUploadResponseSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    dedup = serializers.BooleanField()
    storage_backend = serializers.CharField()
    upload = PresignedUploadSerializer(allow_null=True)


class UploadStatusResponseSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    status = serializers.CharField()
    storage_backend = serializers.CharField()
    visibility = serializers.CharField()
    mime_type = serializers.CharField(allow_blank=True)
    size_bytes = serializers.IntegerField()
    original_filename = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    committed_at = serializers.DateTimeField(allow_null=True)


class AssetErrorResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='error')
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)
