from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models import User, Profile
from .utils.crypto_utils import encrypt_data, decrypt_data
from .constants import (
    MSG_EMAIL_ALREADY_EXISTS,
    MSG_PHONE_ALREADY_EXISTS,
    MSG_CONTACT_REQUIRED,
    MSG_CODE_DIGITS_ONLY,
    MSG_INVALID_CREDENTIALS,
    MSG_WRONG_PHONE_FORMAT,
)
import re

PHONE_REGEX = re.compile(r'^\+?[1-9]\d{6,14}$')


class TokenResponseSerializer(serializers.Serializer):
    """Схема ответа с токенами доступа (Register, Login, Refresh, Recover)."""
    access_token = serializers.CharField(read_only=True)
    access_expires_at = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    refresh_expires_at = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)


class RefreshTokenRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True, help_text='Действующий refresh JWT.')


class RecoverPasswordRequestSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text='Токен из письма восстановления.')
    password_hash = serializers.CharField(
        required=True,
        help_text='Новый пароль (plaintext; имя поля историческое — «hash»).',
    )


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CodeSentResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


class SimpleStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True)


class RateLimitedResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    retry_after = serializers.IntegerField()


class DetailOnlyResponseSerializer(serializers.Serializer):

    detail = serializers.CharField()


class ResetPasswordSuccessSerializer(serializers.Serializer):

    status = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True, required=False, allow_blank=True)


class ResetPasswordPhoneTokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)


class ProfileAssetSerializer(serializers.Serializer):
    asset_id = serializers.CharField()
    filename = serializers.CharField()
    mime_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    url = serializers.URLField(allow_null=True)


class UserProfileAssetsSerializer(serializers.Serializer):

    user_avatar = ProfileAssetSerializer(many=True, read_only=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        if not email and not phone:
            raise serializers.ValidationError(
                MSG_CONTACT_REQUIRED
            )

        if email:
            email_cipher = encrypt_data(email)
            if User.objects.filter(email_cipher=email_cipher).exists():
                raise serializers.ValidationError(
                    {'email': MSG_EMAIL_ALREADY_EXISTS}
                )
            attrs['email_cipher'] = email_cipher
        else:
            attrs['email_cipher'] = None
        if phone:
            if not PHONE_REGEX.match(phone):
                raise serializers.ValidationError(MSG_WRONG_PHONE_FORMAT)
   
            phone_cipher = encrypt_data(phone)
            if User.objects.filter(phone_cipher=phone_cipher).exists():
                raise serializers.ValidationError(
                    {'phone_number': MSG_PHONE_ALREADY_EXISTS}
                )
            attrs['phone_cipher'] = phone_cipher
        else:
            attrs['phone_cipher'] = None
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        passw = attrs.get('password')
        if not email and not phone:
            raise serializers.ValidationError(MSG_CONTACT_REQUIRED)
        user = None

        if email:
            email_cipher = encrypt_data(email)
            user = User.objects.filter(email_cipher=email_cipher).first()

        if not user and phone:
            if not PHONE_REGEX.match(phone):
                raise serializers.ValidationError(MSG_WRONG_PHONE_FORMAT)
   
            phone_cipher = encrypt_data(phone)
            user = User.objects.filter(phone_cipher=phone_cipher).first()

        if not user or not user.check_password(passw):
            raise serializers.ValidationError(MSG_INVALID_CREDENTIALS)

        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        source='user.first_name',
        required=False,
        allow_blank=True,
        allow_null=True)
    last_name = serializers.CharField(
        source='user.last_name',
        required=False,
        allow_blank=True,
        allow_null=True)
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()

    gender = serializers.ChoiceField(
        source='profile.gender',
        choices=Profile.GENDER_CHOICES,
        required=False,
        allow_blank=True,
        allow_null=True)
    birthday = serializers.DateField(
        source='profile.birthday',
        required=False,
        allow_null=True)
    avatar_url = serializers.CharField(
        source='profile.avatar_url',
        read_only=True,
        required=False,
        allow_blank=True,
        max_length=500,
        help_text='Legacy URL (например после OAuth); основной аватар — в assets.user_avatar.',
    )
    assets = serializers.SerializerMethodField()

    @extend_schema_field(UserProfileAssetsSerializer())
    def get_assets(self, obj):
        from apps.core.meta_management.mixins import _build_assets_for_object
        profile = getattr(obj, 'profile', None)
        if not profile:
            return {'user_avatar': []}
        request = self.context.get('request')
        viewer = getattr(request, 'user', None) if request is not None else None
        return _build_assets_for_object(profile, ['user_avatar'], viewer=viewer)

    def get_email(self, obj):
        if hasattr(obj, 'user') and obj.user and obj.user.email_cipher:
            return decrypt_data(obj.user.email_cipher)
        return None

    def get_phone_number(self, obj):
        if hasattr(obj, 'user') and obj.user and obj.user.phone_cipher:
            return decrypt_data(obj.user.phone_cipher)
        return None


class UpdateProfileSerializer(serializers.Serializer):
    _GENDER_IN = {'М': 'М', 'Ж': 'Ж', 'Мужской': 'М', 'Женский': 'Ж'}

    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    avatar_asset_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        gender_raw = attrs.get('gender')
        gender = (gender_raw or '').strip()
        user = self.context.get('user')

        if email:
            email_cipher = encrypt_data(email)
            if User.objects.filter(email_cipher=email_cipher).exclude(
                    pk=user.pk).exists():
                raise serializers.ValidationError(
                    {'email': MSG_EMAIL_ALREADY_EXISTS}
                )
            attrs['email_cipher'] = email_cipher

        if phone:
            if not PHONE_REGEX.match(phone):
                raise serializers.ValidationError('Неверный формат номера телефона')
            phone_cipher = encrypt_data(phone)
            if User.objects.filter(phone_cipher=phone_cipher).exclude(
                    pk=user.pk).exists():
                raise serializers.ValidationError(
                    {'phone_number': MSG_PHONE_ALREADY_EXISTS}
                )
            attrs['phone_cipher'] = phone_cipher

        if gender:
            normalized = self._GENDER_IN.get(gender)
            if normalized is None:
                raise serializers.ValidationError(
                    {'gender': 'Допустимые значения: М, Ж, Мужской, Женский'}
                )
            attrs['gender'] = normalized

        return attrs


class VerifyCodeSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(MSG_CODE_DIGITS_ONLY)
        return value
    

class PhoneRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        phone = (attrs.get('phone_number') or '').strip()
        if not phone:
            raise serializers.ValidationError({'phone_number': 'Нужно указать номер телефона'})
        
        if not PHONE_REGEX.match(phone):
            raise serializers.ValidationError('Неверный формат номера телефона')
        
        phone_cipher = encrypt_data(phone)
        if User.objects.filter(phone_cipher=phone_cipher).exists():
            raise serializers.ValidationError({'phone_number': MSG_PHONE_ALREADY_EXISTS})
        
        attrs['phone_number'] = phone
        return attrs
    

class EmailRegisterSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        if not email:
            raise serializers.ValidationError({'email': 'Необходимо указать email'})
        
        email_cipher = encrypt_data(email)
        if User.objects.filter(email_cipher=email_cipher).exists():
            raise serializers.ValidationError({'email': MSG_EMAIL_ALREADY_EXISTS})
        
        attrs['email'] = email
        return attrs


class VerifyRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(MSG_CODE_DIGITS_ONLY)
        
        return value
    
    def validate(self, attrs):
        phone = (attrs.get('phone_number') or '').strip()
        email = (attrs.get('email') or '').strip()

        if not phone and not email:
            raise serializers.ValidationError(MSG_CONTACT_REQUIRED)
        
        return attrs
    
    
class RecoverPasswordPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(min_length=6, max_length=6)
    
    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(MSG_CODE_DIGITS_ONLY)
        return value


class AvatarBindRequestSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField(required=True)


class AvatarResponseSerializer(serializers.Serializer):
    avatar = serializers.URLField(allow_null=True)
