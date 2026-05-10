from rest_framework import serializers

from apps.users.models import User

from ..models import CourseApplication


class ApplicationUserSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")

    def get_email(self, obj):
        from apps.users.api.utils.crypto_utils import decrypt_data

        if obj.email_cipher:
            return decrypt_data(obj.email_cipher)
        return None


class CourseApplicationSerializer(serializers.ModelSerializer):
    user = ApplicationUserSerializer(read_only=True)

    class Meta:
        model = CourseApplication
        fields = (
            "application_id",
            "status",
            "created_at",
            "updated_at",
            "reviewed_at",
            "reviewed_by",
            "user",
        )
        read_only_fields = fields


class ApplicationReviewedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseApplication
        fields = ("application_id", "status", "reviewed_at", "reviewed_by")
        read_only_fields = fields
