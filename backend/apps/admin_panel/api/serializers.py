from rest_framework import serializers

from apps.admin_panel.models import Invitation
from apps.users.models import User


class TeacherSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")

    def get_email(self, obj):
        from apps.users.api.utils.crypto_utils import decrypt_data

        if obj.email_cipher:
            return decrypt_data(obj.email_cipher)
        return None


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        from apps.users.api.utils.crypto_utils import encrypt_data

        if User.objects.filter(email_cipher=encrypt_data(value)).exists():
            raise serializers.ValidationError("Пользователь с таким email уже зарегистрирован.")
        if Invitation.objects.filter(email=value, used_at__isnull=True).exists():
            pending = Invitation.objects.filter(email=value, used_at__isnull=True).first()
            if not pending.is_expired:
                raise serializers.ValidationError(
                    "Приглашение на этот email уже отправлено и не истекло."
                )
        return value


class InvitationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="invitation_id", read_only=True)
    status = serializers.SerializerMethodField()
    created_by = TeacherSerializer(source="invited_by", read_only=True)

    class Meta:
        model = Invitation
        fields = ("id", "email", "created_by", "created_at", "expires_at", "status")

    def get_status(self, obj):
        return obj.status
