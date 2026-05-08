from rest_framework import serializers

from apps.admin_panel.models import TeacherInvite
from apps.users.models import User


class TeacherSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")

    def get_email(self, obj):
        from apps.users.api.utils.crypto_utils import decrypt_data

        if obj.email_cipher:
            return decrypt_data(obj.email_cipher)
        return None


class TeacherInviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        from apps.users.api.utils.crypto_utils import encrypt_data

        if User.objects.filter(email_cipher=encrypt_data(value)).exists():
            raise serializers.ValidationError("Пользователь с таким email уже зарегистрирован.")
        if TeacherInvite.objects.filter(email=value, used_at__isnull=True).exists():
            pending = TeacherInvite.objects.filter(email=value, used_at__isnull=True).first()
            if not pending.is_expired:
                raise serializers.ValidationError(
                    "Приглашение на этот email уже отправлено и не истекло."
                )
        return value


class TeacherInviteSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    created_by = TeacherSerializer(read_only=True)

    class Meta:
        model = TeacherInvite
        fields = ("id", "email", "created_by", "created_at", "expires_at", "status")

    def get_status(self, obj):
        return obj.status
