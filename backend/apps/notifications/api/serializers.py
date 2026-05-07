from rest_framework import serializers

from ..models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        return None

    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "notification_type",
            "created_at",
            "is_read",
            "image_url",
        )
