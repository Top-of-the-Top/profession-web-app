from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import User


class RegisterSerializer(serializers.Serializer):
  email_cipher = serializers.CharField(required=False, allow_blank=True)
  phone_number_cipher = serializers.CharField(required=False, allow_blank=True)
  pass_hash = serializers.CharField(write_only=True, min_length=8)

  def validate(self, attrs):
    email = (attrs.get('email_cipher') or '').strip()
    phone = (attrs.get('phone_number_cipher') or '').strip()
    if not email and not phone:
      raise serializers.ValidationError(
        'Необходимо указать email_cipher или phone_number_cipher'
      )
    if email and User.objects.filter(email_cipher=email).exists():
      raise serializers.ValidationError(
        {'email_cipher': 'Пользователь с таким email уже существует'}
      )
    if phone and User.objects.filter(phone_cipher=phone).exists():
      raise serializers.ValidationError(
        {'phone_number_cipher': 'Пользователь с таким телефоном уже существует'}
      )
    attrs['email_cipher'] = email or None
    attrs['phone_number_cipher'] = phone or None
    return attrs


class LoginSerializer(serializers.Serializer):
  email_cipher = serializers.CharField(required=False, allow_blank=True)
  phone_number_cipher = serializers.CharField(required=False, allow_blank=True)
  pass_hash = serializers.CharField(write_only=True)

  def validate(self, attrs):
    email = (attrs.get('email_cipher') or '').strip()
    phone = (attrs.get('phone_number_cipher') or '').strip()
    password = attrs.get('pass_hash')
    if not email and not phone:
      raise serializers.ValidationError(
        'Необходимо указать email_cipher или phone_number_cipher'
      )
    user = None
    if email:
      user = User.objects.filter(email_cipher=email).first()
    if not user and phone:
      user = User.objects.filter(phone_cipher=phone).first()
    if not user or not user.check_password(password):
      raise serializers.ValidationError('Неверный email/телефон или пароль')
    attrs['user'] = user
    return attrs
