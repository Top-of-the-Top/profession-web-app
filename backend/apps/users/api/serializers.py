from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import User, Profile
from .utils import encrypt_data, decrypt_data
import re


class TokenResponseSerializer(serializers.Serializer):
    """Схема ответа с токенами доступа (Register, Login, Refresh, Recover)."""
    access_token = serializers.CharField(read_only=True)
    access_expires_at = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    refresh_expires_at = serializers.CharField(read_only=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        if not email and not phone:
            raise serializers.ValidationError(
                'Необходимо указать email или phone_number'
            )

        if email:
            email_cipher = encrypt_data(email)
            if User.objects.filter(email_cipher=email_cipher).exists():
                raise serializers.ValidationError(
                    {'email': 'Пользователь с таким email уже существует'}
                )
            attrs['email_cipher'] = email_cipher
        else:
            attrs['email_cipher'] = None
        if phone:
            phone_cipher = encrypt_data(phone)
            if User.objects.filter(phone_cipher=phone_cipher).exists():
                raise serializers.ValidationError(
                    {'phone_number': 'Пользователь с таким телефоном уже существует'}
                )
            attrs['phone_cipher'] = phone_cipher
        else:
            attrs['phone_cipher'] = None
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        passw = attrs.get('password')
        if not email and not phone:
            raise serializers.ValidationError(
                'Необходимо указать email или phone_number'
            )
        user = None

        if email:
            email_cipher = encrypt_data(email)
            user = User.objects.filter(email_cipher=email_cipher).first()

            if not user:
                raise serializers.ValidationError('Неверная почта')

        if not user and phone:
            phone_cipher = encrypt_data(phone)
            user = User.objects.filter(phone_cipher=phone_cipher).first()

            if not user:
                raise serializers.ValidationError('Неверный номер телефона')


        if not user.check_password(passw):
            raise serializers.ValidationError('Неверный пароль')

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

    gender = serializers.CharField(
        source='profile.gender',
        required=False,
        allow_blank=True,
        allow_null=True)
    birthday = serializers.DateField(
        source='profile.birthday',
        required=False,
        allow_null=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.avatar_url
        return None

    def get_email(self, obj):
        if hasattr(obj, 'user') and obj.user and obj.user.email_cipher:
            return decrypt_data(obj.user.email_cipher)
        return None

    def get_phone_number(self, obj):
        if hasattr(obj, 'user') and obj.user and obj.user.phone_cipher:
            return decrypt_data(obj.user.phone_cipher)
        return None


class UpdateProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    avatar = serializers.ImageField(required=False, allow_null=True)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone = (attrs.get('phone_number') or '').strip()
        gender = (attrs.get('gender') or '').strip()
        avatar = attrs.get('avatar')
        user = self.context.get('user')

        if email:
            email_cipher = encrypt_data(email)
            if User.objects.filter(email_cipher=email_cipher).exclude(
                    pk=user.pk).exists():
                raise serializers.ValidationError(
                    {'email': 'Пользователь с таким email уже существует'}
                )
            attrs['email_cipher'] = email_cipher

        if phone:
            phone_cipher = encrypt_data(phone)
            if User.objects.filter(phone_cipher=phone_cipher).exclude(
                    pk=user.pk).exists():
                raise serializers.ValidationError(
                    {'phone_number': 'Пользователь с таким телефоном уже существует'}
                )
            attrs['phone_cipher'] = phone_cipher

        if gender and gender not in ('Мужской', 'Женский'):
            raise serializers.ValidationError(
                {'gender': 'Допустимые значения: Мужской, Женский'}
            )

        if avatar and avatar.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                {'avatar': 'Размер файла не должен превышать 5 МБ'}
            )

        return attrs

class VerifyCodeSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Код должен содержать только цифры")
        return value
    

class PhoneRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        phone = (attrs.get('phone_number') or '').strip()
        if not phone:
            raise serializers.ValidationError({'phone_number': 'Нужно указать номер телефона'})
        
        phone_cipher = encrypt_data(phone)
        if User.objects.filter(phone_cipher=phone_cipher).exists():
            raise serializers.ValidationError({'phone_number': 'Пользователь с таким телефоном уже существует'})
        
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
            raise serializers.ValidationError({'email': 'Пользователь с таким email уже существует'})
        
        attrs['email'] = email
        return attrs


class VerifyRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('Код должен соержать только цифры')
        
        return value
    
    def validate(self, attrs):
        phone = (attrs.get('phone_number') or '').strip()
        email = (attrs.get('email') or '').strip()

        if not phone and not email:
            raise serializers.ValidationError('Нужно указать phone_number или email')
        
        return attrs
    
    
class RecoverPasswordPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(min_length=6, max_length=6)
    
    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Код должен состоять только из цифр")
        return value
