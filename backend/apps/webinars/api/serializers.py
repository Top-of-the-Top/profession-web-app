from rest_framework import serializers
from ..models import Webinar, Recording


class WebinarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webinar
        fields = [
            'webinar_id', 'lesson', 'status',
            'started_by', 'started_at', 'ended_at',
        ]
        read_only_fields = [
            'webinar_id', 'started_by', 'started_at', 'ended_at',
        ]


class WebinarTokenSerializer(serializers.Serializer):
    rtc_token = serializers.CharField()
    agora_app_id = serializers.CharField()
    channel_name = serializers.CharField()
    uid = serializers.IntegerField()
    whiteboard_app_id = serializers.CharField()
    whiteboard_room_uuid = serializers.CharField()
    whiteboard_room_token = serializers.CharField()
    whiteboard_region = serializers.CharField()
    role = serializers.CharField()


class RecordingListItemSerializer(serializers.ModelSerializer):
    kinescope_embed_url = serializers.SerializerMethodField()

    class Meta:
        model = Recording
        fields = (
            'recording_id',
            'started_at',
            'ended_at',
            'status',
            'kinescope_upload_status',
            'kinescope_embed_url',
            'whiteboard_pdf_url',
        )

    def get_kinescope_embed_url(self, obj):
        if obj.kinescope_upload_status != 'ready' or not obj.kinescope_video_id:
            return ''
        
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        
        from .utils.kinescope_utils import generate_drm_token
        
        drm_token = generate_drm_token(user_id=request.user.pk, video_id=obj.kinescope_video_id)
        return f'https://kinescope.io/embed/{obj.kinescope_video_id}?drmauthtoken={drm_token}'
    