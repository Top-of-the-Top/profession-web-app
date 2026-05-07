from ..models import Notification
from rest_framework import serializers


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        exclude = ('read_by',)
