from rest_framework import serializers

from apps.core.services.factory import build_access_api

from ..models import Webinar, Recording


RECORDING_WHITEBOARD_CONTEXT_KEY = 'whiteboard_url_by_recording_id'


def build_recording_whiteboard_map(recordings, access=None):
    access = access or build_access_api()
    try:
        return access.resolve_bound_urls_map(recordings, role='whiteboard_pdf')
    except Exception:
        return {}


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
    webinar_id = serializers.UUIDField()
    rtc_token = serializers.CharField()
    agora_app_id = serializers.CharField()
    channel_name = serializers.CharField()
    uid = serializers.IntegerField()
    user_name = serializers.CharField()
    whiteboard_app_id = serializers.CharField()
    whiteboard_room_uuid = serializers.CharField()
    whiteboard_room_token = serializers.CharField()
    whiteboard_region = serializers.CharField()
    role = serializers.CharField()


class WebinarStartResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    webinar_id = serializers.UUIDField()


class WebinarRecordingStartResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    recording_id = serializers.UUIDField()


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RecordingListItemSerializer(serializers.ModelSerializer):
    kinescope_embed_url = serializers.SerializerMethodField()
    whiteboard_pdf_url = serializers.SerializerMethodField()

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

    def get_whiteboard_pdf_url(self, obj):
        mapping = self.context.get(RECORDING_WHITEBOARD_CONTEXT_KEY)
        if mapping is not None:
            url = mapping.get(str(obj.recording_id))
            if url:
                return url
        else:
            access = build_access_api()
            try:
                url = access.resolve_bound_url(obj, role='whiteboard_pdf')
            except Exception:
                url = None
            if url:
                return url
        return obj.whiteboard_pdf_url or ''
    