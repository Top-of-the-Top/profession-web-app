from django.shortcuts import render

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import User
from .serializers import RegisterSerializer, LoginSerializer
from .utils import get_tokens_for_user
from rest_framework_simplejwt.tokens import RefreshToken

from django.core.mail import send_mail
from django.conf import settings
from .utils import set_reset_token, decrypt_email
import os
from django.utils import timezone


class RegisterView(APIView):
  permission_classes = []

  def post(self, request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
      return Response(
        serializer.errors,
        status=status.HTTP_403_FORBIDDEN
      )
    data = serializer.validated_data
    email = data.get('email_cipher') or None
    phone = data.get('phone_number_cipher') or None
    password = data['pass_hash']

    user = User.objects.create_user(
      email_cipher=email,
      phone_cipher=phone,
      password=password
    )

    return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class LoginView(APIView):
  permission_classes = []

  def post(self, request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
      return Response(
        serializer.errors,
        status=status.HTTP_403_FORBIDDEN
      )
    user = serializer.validated_data['user']
    return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
  permission_classes = []

  def post(self, request):
    refresh_token = request.data.get('refresh_token')
    if not refresh_token:
      return Response(
        {'detail': 'refresh_token обязателен'},
        status=status.HTTP_403_FORBIDDEN
      )
    try:
      refresh = RefreshToken(refresh_token)
      user = User.objects.get(id=refresh['user_id'])
      new_refresh = RefreshToken.for_user(user)
      access = new_refresh.access_token
      from datetime import datetime, timezone
      return Response({
        'access_token': str(new_refresh.access_token),
        'access_expires_at': datetime.fromtimestamp(access['exp'], tz=timezone.utc).isoformat(),
        'refresh_token': str(new_refresh),
        'refresh_expires_at': datetime.fromtimestamp(new_refresh['exp'], tz=timezone.utc).isoformat(),
      }, status=status.HTTP_200_OK)
    except Exception:
      return Response(
        {'detail': 'Невалидный или истекший refresh_token'},
        status=status.HTTP_403_FORBIDDEN
      )


class ResetPasswordView(APIView):
  permission_classes = []

  def post(self, request):
    email = (request.data.get('email_cipher') or '').strip()
    phone = (request.data.get('phone_cipher') or '').strip()

    if not email and not phone:
      return Response(
        {'detail': f'Необходимо указать email_cipher или phone_number_cipher'},
        status=status.HTTP_403_FORBIDDEN
      )

    user = None
    if email:
      user = User.objects.filter(email_cipher=email).first()
    if not user and phone:
      user = User.objects.filter(phone_cipher=phone).first()
    if not user:
      return Response(
        {'detail': f'Необходимо указать email_cipher или phone_number_cipher phone'},
        status=status.HTTP_403_FORBIDDEN
      )

    token = set_reset_token(user)
    frontend_host = os.environ.get('FRONTEND_HOST')
    recover_url = f"{frontend_host}/recover?token={token}"

    decrypted_email = None
    if user.email_cipher:
      decrypted_email = decrypt_email(user.email_cipher)
    recipient_email = decrypted_email if decrypted_email else ''
    
    try:
      result = send_mail(
        subject='Сброс пароля',
        message=f'Перейдите по ссылке для сброса пароля: {recover_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        fail_silently=False,
      )
      print(f'Письмо отправлено успешно. Результат: {result}')
    except Exception as e:
      print(f'Ошибка при отправке письма: {type(e).__name__}: {str(e)}')
      return Response(
        {'detail': f'Ошибка отправки письма: {str(recipient_email)}'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
      )
    return Response(
      {'status': 'success'},
      status=status.HTTP_200_OK
    )


class RecoverPasswordView(APIView):
  permission_classes = []

  def patch(self, request):
    token = request.data.get('token')
    password = request.data.get('password_hash')
    if not token or not password:
      return Response(
        {'detail': 'token и password обязательны'},
        status=status.HTTP_403_FORBIDDEN
      )
    user = User.objects.filter(
      reset_token=token,
      reset_token_expires__gt=timezone.now()
    ).first()
    if not user:
      return Response(
        {'detail': 'Невалидный или истёкший токен'},
        status=status.HTTP_403_FORBIDDEN
      )
    user.set_password(password)
    user.reset_token = None
    user.reset_token_expires = None
    user.save(update_fields=['password', 'reset_token', 'reset_token_expires'])

    return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)
  