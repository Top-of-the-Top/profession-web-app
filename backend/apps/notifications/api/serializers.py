from ..models import Notification
from rest_framework import serializers

class NotificationSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = Notification
        fields = '__all__'
