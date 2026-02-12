from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import User
from .utils import encrypt_data


class RegisterSerializer(serializers.Serializer):
  email = serializers.CharField(required=False, allow_blank=True, allow_null=True)
  phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
  pass_hash = serializers.CharField(write_only=True, min_length=8)

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
  phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
  pass_hash = serializers.CharField(write_only=True)

  def validate(self, attrs):
    email = (attrs.get('email') or '').strip()
    phone = (attrs.get('phone_number') or '').strip()
    password = attrs.get('pass_hash')
    if not email and not phone:
      raise serializers.ValidationError(
        'Необходимо указать email или phone_number'
      )
    user = None
    if email:
      email_cipher = encrypt_data(email)
      user = User.objects.filter(email_cipher=email_cipher).first()
    if not user and phone:
      phone_cipher = encrypt_data(phone)
      user = User.objects.filter(phone_cipher=phone_cipher).first()
    if not user or not user.check_password(password):
      raise serializers.ValidationError('Неверная почта/телефон/пароль')
    attrs['user'] = user
    return attrs
