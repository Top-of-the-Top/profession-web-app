from django.utils import timezone
import os
import logging
import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import redirect
from django.conf import settings
from urllib.parse import urlencode
import httpx
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .errors import VerificationError
from ..models import User, Profile
from .constants import (
    MSG_CONTACT_REQUIRED,
    MSG_RATE_LIMITED,
    MSG_USER_NOT_FOUND,
    MSG_EMAIL_ALREADY_EXISTS,
    MSG_PHONE_ALREADY_EXISTS,
)
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    TokenResponseSerializer,
    VerifyCodeSerializer,
    PhoneRegisterSerializer,
    EmailRegisterSerializer,
    VerifyRegisterSerializer,
    RecoverPasswordPhoneSerializer,
    AvatarBindRequestSerializer,
    AvatarResponseSerializer,
)
from apps.core.api.responses import asset_error_response
from apps.core.services.errors import AssetError
from apps.core.services.factory import build_access_api, build_binding_api
from .utils import (
    get_tokens_for_user,
    send_verification_sms,
    send_verification_email,
    send_reset_password_email,
    generate_verification_code_for_user,
    verify_code,
    encrypt_data,
    send_reset_password_sms,
    set_reset_token,
    generate_registration_code,
    verify_registration_code,
    check_contact_rate_limit,
)
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from django.db import IntegrityError

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300

SCHEMA_401 = {
    "type": "object",
    "properties": {"detail": {"type": "string", "description": "Токен отсутствует или недействителен."}},
}
SCHEMA_403 = {
    "type": "object",
    "properties": {"detail": {"type": "string", "description": "Доступ запрещён."}},
}
SCHEMA_VALIDATION_ERROR = {
    "type": "object",
    "description": "Объект с ошибками валидации по полям.",
}
SCHEMA_500 = {
    "type": "object",
    "properties": {
        "detail": {"type": "string", "description": "Ошибка сервера.", "example": "Ошибка отправки письма."},
    },
}

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Регистрация пользователя",
        description=(
            "Двухэтапная регистрация. "
            "Передайте email или phone_number с password. "
            "На указанный контакт отправляется 6 значный код. "
            "Для завершения отправьте код на /api/auth/register/verify/."
        ),
        tags=["Users"],
        request=RegisterSerializer,
        responses={
            200: {
                "description": "Код отправлен.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "code_sent"},
                        "detail": {"type": "string"},
                    },
                },
            },
            403: {
                "description": "Ошибка валидации.",
                "schema": SCHEMA_VALIDATION_ERROR
            },
            429: {
                "description": "Слишком частые запросы.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"},
                        "retry_after": {"type": "integer"},
                    },
                },
            },
        },
    )
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        phone = (request.data.get('phone_number') or '').strip()

        if not email and not phone:
            return Response(
                {'detail': MSG_CONTACT_REQUIRED},
                status=status.HTTP_403_FORBIDDEN,
            )

        if phone and not email:
            serializer = PhoneRegisterSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

            phone_numder = serializer.validated_data['phone_number']
            password = serializer.validated_data['password']

            is_allowed, retry_after = check_contact_rate_limit(phone_numder, 'phone')
            if not is_allowed:
                return Response(
                    {
                        'detail': MSG_RATE_LIMITED.format(retry_after=retry_after),
                        'retry_after': retry_after,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            code = generate_registration_code(phone_numder, password, contact_type='phone')
            send_verification_sms(phone_numder, code)

            return Response(
                {'status': 'code_sent', 'detail': 'Код подтверждения отправлен на телефон.'},
                status=status.HTTP_200_OK,
            )
        if email:
            serializer = EmailRegisterSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

            email_value = serializer.validated_data['email']
            password = serializer.validated_data['password']

            is_allowed, retry_after = check_contact_rate_limit(email_value, 'email')
            if not is_allowed:
                return Response(
                    {
                        'detail': MSG_RATE_LIMITED.format(retry_after=retry_after),
                        'retry_after': retry_after,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            code = generate_registration_code(email_value, password, contact_type='email')
            send_verification_email(email_value, code)

            return Response(
                {'status': 'code_sent', 'detail': 'Код подтверждения отправлен на почту.'},
                status=status.HTTP_200_OK,
            )


class VerifyRegisterView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Подтверждение регистрации",
        description=(
            "Второй шаг регистрации. "
            "Передайте phone_number или email и 6 значный код. "
            "При успехе создаётся аккаунт и возвращаются JWT токены."
        ),
        tags=["Users"],
        request=VerifyRegisterSerializer,
        responses={
            200: TokenResponseSerializer,
            400: {
                "description": "Неверный или истёкший код.",
                "schema": SCHEMA_VALIDATION_ERROR,
            },
        },
    )
    def post(self, request):
        serializer = VerifyRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = (serializer.validated_data.get('phone_number') or '').strip()
        email = (serializer.validated_data.get('email') or '').strip()
        user_code = serializer.validated_data['code']

        if phone:
            contact = phone
            contact_type = 'phone'
        else:
            contact = email
            contact_type = 'email'

        try:
            reg_data = verify_registration_code(contact, user_code, contact_type)
        except VerificationError as e:
            return Response(
                {'error': e.code, 'detail': e.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reg_data['contact_type'] == 'phone':
            phone_cipher = encrypt_data(reg_data['contact'])
            user = User.objects.create_user(phone_cipher=phone_cipher)
        else:
            email_cipher = encrypt_data(reg_data['contact'])
            user = User.objects.create_user(email_cipher=email_cipher)

        user.password = reg_data['password_hash']
        user.save(update_fields=['password'])

        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Вход пользователя",
        description=(
            "Аутентификация по email или phone_number и паролю. "
            "При успехе возвращаются JWT токены."
        ),
        tags=["Users"],
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            400: {"description": "Ошибка валидации.", "schema": SCHEMA_VALIDATION_ERROR},
        },
    )
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        phone = (request.data.get('phone_number') or '').strip()
        contact = email or phone

        if contact:
            contact_hash = hashlib.sha256(contact.encode()).hexdigest()[:16]
            lockout_key = f'login_lockout_{contact_hash}'
            attempts_key = f'login_attempts_{contact_hash}'

            if cache.get(lockout_key):
                ttl = getattr(cache, 'ttl', lambda k: LOGIN_LOCKOUT_SECONDS)(lockout_key)
                return Response(
                    {
                        'detail': f'Слишком много попыток. Повторите через {ttl} секунд',
                        'retry_after': ttl,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            if contact:
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=LOGIN_LOCKOUT_SECONDS)
                if attempts >= MAX_LOGIN_ATTEMPTS:
                    cache.set(lockout_key, 1, timeout=LOGIN_LOCKOUT_SECONDS)
                    cache.delete(attempts_key)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        if contact:
            cache.delete(attempts_key)

        user = serializer.validated_data['user']
        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Обновление токенов",
        description=(
            "Выдаёт новую пару access и refresh токенов по действующему refresh_token."
        ),
        tags=["Users"],
        responses={
            200: TokenResponseSerializer,
            401: {"description": "refresh_token отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response(
                {'detail': 'refresh_token обязателен'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            refresh = RefreshToken(refresh_token)
            user = User.objects.get(id=refresh['user_id'])
            return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {'detail': 'Невалидный или истекший refresh_token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ResetPasswordView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Сброс пароля",
        description=(
            "Запрос на сброс пароля. "
            "Передайте email или phone_number. "
            "На email отправляется ссылка, на телефон SMS код."
        ),
        tags=["Users"],
        responses={
            200: {"description": "Ссылка или код отправлены.",
                  "schema": {"type": "object", "properties": {"status": {"type": "string", "example": "success"}}}},
            403: {"description": "Контакт не указан или пользователь не найден.", "schema": SCHEMA_403},
            500: {"description": "Ошибка отправки.", "schema": SCHEMA_500},
        },
    )
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        phone = (request.data.get('phone_number') or '').strip()

        if not email and not phone:
            return Response(
                {'detail': MSG_CONTACT_REQUIRED},
                status=status.HTTP_403_FORBIDDEN
            )

        user = None
        if email:
            email_cipher = encrypt_data(email)
            user = User.objects.filter(email_cipher=email_cipher).first()
        if not user and phone:
            phone_cipher = encrypt_data(phone)
            user = User.objects.filter(phone_cipher=phone_cipher).first()
        if not user:
            return Response(
                {'detail': MSG_USER_NOT_FOUND},
                status=status.HTTP_403_FORBIDDEN
            )

        if email:
            token = set_reset_token(user)
            frontend_host = os.environ.get('FRONTEND_HOST')
            recover_url = f"{frontend_host}/recover?token={token}"
            result = send_reset_password_email(email, recover_url)
            if not result[0]:
                return Response(
                    {'detail': 'Ошибка отправки письма'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return Response({'status': 'success'}, status=status.HTTP_200_OK)

        is_allowed, retry_after = check_contact_rate_limit(phone, 'phone')
        if not is_allowed:
            return Response(
                {
                    'detail': MSG_RATE_LIMITED.format(retry_after=retry_after),
                    'retry_after': retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = generate_verification_code_for_user(
            user_id=user.id,
            contact_type='reset_phone',
            new_contact=phone,
        )
        result = send_reset_password_sms(phone, code)
        if not result[0]:
            return Response(
                {'detail': 'Ошибка отправки SMS'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {'status': 'success', 'detail': 'Код для сброса пароля отправлен на телефон.'},
            status=status.HTTP_200_OK
        )


class RecoverPasswordView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Установка нового пароля",
        description=(
            "Завершение сброса пароля. "
            "Передайте token (из письма) и password_hash (новый пароль). "
            "При успехе возвращаются JWT токены."
        ),
        tags=["Users"],
        responses={
            200: TokenResponseSerializer,
            403: {"description": "Токен отсутствует, невалиден или истёк.", "schema": SCHEMA_403},
        },
    )
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
        user.reset_token = ''
        user.reset_token_expires = None
        user.save(update_fields=['password', 'reset_token', 'reset_token_expires'])

        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class RecoverPasswordPhoneView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Проверка SMS кода для сброса пароля",
        description=(
            "Передайте phone_number и 6 значный код из SMS. "
            "При успехе возвращается reset_token для установки нового пароля."
        ),
        tags=["Users"],
        request=RecoverPasswordPhoneSerializer,
        responses={
            200: {
                "description": "Код подтверждён, токен выдан.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Токен для сброса пароля"},
                    },
                },
            },
            400: {
                "description": "Неверный или истёкший код.",
                "schema": SCHEMA_VALIDATION_ERROR,
            },
            403: {
                "description": "Пользователь не найден.",
                "schema": SCHEMA_403,
            },
        },
    )
    def post(self, request):
        serializer = RecoverPasswordPhoneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number'].strip()
        user_code = serializer.validated_data['code']

        phone_cipher = encrypt_data(phone_number)
        user = User.objects.filter(phone_cipher=phone_cipher).first()
        if not user:
            return Response(
                {'detail': MSG_USER_NOT_FOUND},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            verify_code(
                user_id=user.id,
                contact_type='reset_phone',
                user_code=user_code,
            )
        except VerificationError as e:
            return Response(
                {'error': e.code, 'detail': e.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = set_reset_token(user)
        return Response({'token': token}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Получение профиля",
        description="Возвращает профиль текущего пользователя.",
        tags=["Users"],
        responses={
            200: UserProfileSerializer,
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        class UserProfileWrapper:
            def __init__(self, user, profile):
                self.user = user
                self.profile = profile

        wrapper = UserProfileWrapper(user, profile)
        serializer = UserProfileSerializer(wrapper)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Обновление профиля",
        description="Частичное обновление профиля текущего пользователя.",
        tags=["Users"],
        request=UpdateProfileSerializer,
        responses={
            200: {"description": "Профиль обновлён.",
                  "schema": {"type": "object", "properties": {"status": {"type": "string", "example": "success"}}}},
            400: {"description": "Ошибка валидации.", "schema": SCHEMA_VALIDATION_ERROR},
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def patch(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(data=request.data, context={'user': user})
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        data = serializer.validated_data
        profile, _ = Profile.objects.get_or_create(user=user)

        if 'email' in data and data['email']:
            new_email = data['email']

            code = generate_verification_code_for_user(
                user_id=user.id,
                contact_type='email',
                new_contact=new_email
            )
            send_verification_email(new_email, code)

        if 'phone_number' in data and data['phone_number']:
            new_phone = data['phone_number']

            is_allowed, retry_after = check_contact_rate_limit(new_phone, 'phone')
            if not is_allowed:
                return Response(
                    {
                        'detail': MSG_RATE_LIMITED.format(retry_after=retry_after),
                        'retry_after': retry_after,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            code = generate_verification_code_for_user(
                user_id=user.id,
                contact_type='phone',
                new_contact=new_phone
            )
            send_verification_sms(new_phone, code)

        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        user.save()

        if 'gender' in data:
            profile.gender = data['gender']
        if 'birthday' in data:
            profile.birthday = data['birthday']
        profile.save()

        return Response(
            {'status': 'success'},
            status=status.HTTP_200_OK
        )


class VerifyEmailChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Подтверждение смены email",
        description=(
            "После PATCH профиля с новым email на почту уходит код. "
            "Передайте 6-значный код из письма."
        ),
        tags=["Users"],
        request=VerifyCodeSerializer,
        responses={
            200: {
                "description": "Email обновлён.",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "example": "success"}},
                },
            },
            400: {
                "description": "Неверный код, неверный формат, дубликат email или ошибка валидации.",
                "schema": SCHEMA_VALIDATION_ERROR,
            },
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_email = verify_code(
                user_id=request.user.id,
                contact_type='email',
                user_code=serializer.validated_data['code']
            )
        except VerificationError as e:
            return Response(
                {'error': e.code, 'detail': e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_cipher = encrypt_data(new_email)
        if User.objects.filter(email_cipher=new_cipher).exclude(pk=request.user.pk).exists():
            return Response(
                {'detail': MSG_EMAIL_ALREADY_EXISTS},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.email_cipher = new_cipher
        try:
            request.user.save(update_fields=['email_cipher'])
        except IntegrityError:
            return Response(
                {'detail': MSG_EMAIL_ALREADY_EXISTS},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class VerifyPhoneChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Подтверждение смены телефона",
        description=(
            "После PATCH профиля с новым номером на телефон уходит SMS с кодом. "
            "Передайте 6-значный код из сообщения."
        ),
        tags=["Users"],
        request=VerifyCodeSerializer,
        responses={
            200: {
                "description": "Телефон обновлён.",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "example": "success"}},
                },
            },
            400: {
                "description": "Неверный код, неверный формат, дубликат телефона или ошибка валидации.",
                "schema": SCHEMA_VALIDATION_ERROR,
            },
            401: {"description": "Токен отсутствует или недействителен.", "schema": SCHEMA_401},
        },
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_phone = verify_code(
                user_id=request.user.id,
                contact_type='phone',
                user_code=serializer.validated_data['code']
            )
        except VerificationError as e:
            return Response(
                {'error': e.code, 'detail': e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_cipher = encrypt_data(new_phone)
        if User.objects.filter(phone_cipher=new_cipher).exclude(pk=request.user.pk).exists():
            return Response(
                {'detail': MSG_PHONE_ALREADY_EXISTS},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.phone_cipher = new_cipher
        try:
            request.user.save(update_fields=['phone_cipher'])
        except IntegrityError:
            return Response(
                {'detail': MSG_PHONE_ALREADY_EXISTS},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class YandexCallbackAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')

        params = {"provider": "yandex"}

        if code:
            cache.set(f"oauth:yandex:state:{state}", 1, timeout=600)
            params.update({'code': code, 'state': state})
        elif error:
            params.update({
                'error': error,
                'error_description': request.query_params.get('error_description', '')
            })
            if state:
                params['state'] = state
        else:
            params['error'] = 'invalid_callback_payload'

        target_url = f"{settings.FRONTEND_OAUTH_YANDEX_REDIRECT_URI}?{urlencode(params)}"
        return redirect(target_url)


class YandexOauth2APIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _validate_state(self, state):
        key = f"oauth:yandex:state:{state}"
        return bool(cache.delete(key))

    def _exchange_code_for_token(self, code):
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.YANDEX_CLIENT_ID,
            "client_secret": settings.YANDEX_CLIENT_SECRET,
        }
        try:
            response = httpx.post("https://oauth.yandex.ru/token", data=data, timeout=5.0)
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError:
            return None
        return None

    def _get_yandex_user_info(self, token):
        headers = {"Authorization": f"OAuth {token}"}
        try:
            resp = httpx.get("https://login.yandex.ru/info?format=json", headers=headers, timeout=5.0)
            return resp.json() if resp.status_code == 200 else {}
        except httpx.RequestError:
            return {}

    def _sync_user_profile(self, user, user_info, *, is_new):
        user_fields_changed = []

        first_name = (user_info.get('first_name') or '').strip()
        last_name = (user_info.get('last_name') or '').strip()

        if first_name and (is_new or not user.first_name):
            user.first_name = first_name
            user_fields_changed.append('first_name')
        if last_name and (is_new or not user.last_name):
            user.last_name = last_name
            user_fields_changed.append('last_name')

        if user_fields_changed:
            user.save(update_fields=user_fields_changed)

        profile, _ = Profile.objects.get_or_create(user=user)
        profile_fields_changed = []

        birthday_raw = user_info.get('birthday')
        if birthday_raw and (is_new or not profile.birthday):
            from datetime import date
            try:
                parsed_birthday = date.fromisoformat(birthday_raw)
                if parsed_birthday.year > 0:
                    profile.birthday = parsed_birthday
                    profile_fields_changed.append('birthday')
            except (ValueError, AttributeError):
                pass

        sex = user_info.get('sex')
        if sex and (is_new or not profile.gender):
            gender_map = {'male': 'М', 'female': 'Ж'}
            mapped = gender_map.get(sex)
            if mapped:
                profile.gender = mapped
                profile_fields_changed.append('gender')

        if profile_fields_changed:
            profile.save(update_fields=profile_fields_changed)

    def post(self, request):
        code = request.data.get('code')
        state = request.data.get('state')

        if not code or not state:
            return Response({"error": "invalid_request", "detail": "Code and state are required."}, status=400)

        if not self._validate_state(state):
            return Response(
                {"error": "invalid_state", "detail": "OAuth state is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        yandex_tokens = self._exchange_code_for_token(code)
        if not yandex_tokens:
            return Response({"error": "invalid_code"}, status=400)

        user_info = self._get_yandex_user_info(yandex_tokens['access_token'])
        email = user_info.get('default_email')
        default_phone = user_info.get('default_phone') or {}
        phone = default_phone.get('number') if isinstance(default_phone, dict) else None

        if not email and not phone:
            return Response({"error": "missing_required_profile_data"}, status=400)

        email_enc = encrypt_data(str(email)) if email else None
        phone_enc = encrypt_data(str(phone)) if phone else None

        user = None
        if email_enc:
            user = User.objects.filter(email_cipher=email_enc).first()
        if not user and phone_enc:
            user = User.objects.filter(phone_cipher=phone_enc).first()

        is_new = user is None
        if is_new:
            user = User.objects.create(
                email_cipher=email_enc,
                phone_cipher=phone_enc,
                role='student',
            )

        self._sync_user_profile(user, user_info, is_new=is_new)

        return Response(get_tokens_for_user(user), status=200)


class VKCallbackAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        device_id = request.query_params.get('device_id')
        error = request.query_params.get('error')

        params = {"provider": "vk"}

        if code:
            cache.set(f"oauth:vk:state:{state}", 1, timeout=600)
            params.update({
                'code': code,
                'state': state,
                'device_id': device_id
            })
        elif error:
            params.update({
                'error': error,
                'error_description': request.query_params.get('error_description', '')
            })
            if state:
                params['state'] = state
        else:
            params['error'] = 'invalid_callback_payload'

        target_url = f"{settings.FRONTEND_OAUTH_VK_REDIRECT_URI}?{urlencode(params)}"
        return redirect(target_url)


class VKOAauth2APIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _validate_state(self, state):
        key = f"oauth:vk:state:{state}"
        return bool(cache.delete(key))

    def _sync_vk_profile(self, user, vk_user, *, is_new):
        user_fields_changed = []

        first_name = vk_user.get('first_name', '').strip()
        last_name = vk_user.get('last_name', '').strip()

        if first_name and (is_new or not user.first_name):
            user.first_name = first_name
            user_fields_changed.append('first_name')
        if last_name and (is_new or not user.last_name):
            user.last_name = last_name
            user_fields_changed.append('last_name')

        if user_fields_changed:
            user.save(update_fields=user_fields_changed)

        profile, _ = Profile.objects.get_or_create(user=user)

        if is_new or not profile.avatar:
            profile.avatar = vk_user.get('avatar')

        vk_sex = vk_user.get('sex')
        if vk_sex and (is_new or not profile.gender):
            profile.gender = 'М' if vk_sex == 2 else 'Ж'

        profile.save()

    def _exchange_code_for_tokens(self, code, code_verifier, device_id):
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "device_id": device_id,
            "client_id": settings.VK_CLIENT_ID,
            "client_secret": settings.VK_CLIENT_SECRET,
            "redirect_uri": settings.VK_REDIRECT_URI,
        }
        try:
            response = httpx.post("https://id.vk.com/oauth2/auth", data=data, timeout=5.0)

            if response.status_code != 200:
                logger.error(f"VK Exchange Failed: Status {response.status_code}, Response: {response.text}")
                return None

            logger.info("VK Exchange Success: Tokens received.")
            return response.json()
        except httpx.RequestError as e:
            logger.exception(f"VK Exchange Network Error: {str(e)}")
            return None

    def _get_vk_user_info(self, access_token):
        data = {
            "access_token": access_token,
            "client_id": settings.VK_CLIENT_ID,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            resp = httpx.post(
                "https://id.vk.ru/oauth2/user_info",
                data=data,
                headers=headers,
                timeout=5.0
            )

            if resp.status_code == 200:
                data = resp.json()
                if 'error' in data:
                    return {}

                return data

            return {}

        except httpx.RequestError as e:
            logger.exception(f"VK UserInfo Connection Error: {str(e)}")
            return {}

    def post(self, request):
        code = request.data.get('code')
        state = request.data.get('state')
        code_verifier = request.data.get('code_verifier')
        device_id = request.data.get('device_id')

        if not all([code, state, code_verifier, device_id]):
            return Response({"error": "invalid_request"}, status=400)

        if not self._validate_state(state):
            return Response({"error": "invalid_state"}, status=400)

        vk_tokens = self._exchange_code_for_tokens(code, code_verifier, device_id)
        if not vk_tokens or 'access_token' not in vk_tokens:
            return Response({"error": "invalid_code"}, status=400)

        user_info = self._get_vk_user_info(vk_tokens['access_token'])
        vk_user = user_info.get('user', {})
        email = vk_user.get('email')
        phone = vk_user.get('phone')

        if not email and not phone:
            return Response({
                "error": "missing_required_profile_data",
                "details": user_info
            }, status=400)

        email_enc = encrypt_data(str(email)) if email else None
        phone_enc = encrypt_data(str(phone)) if phone else None

        user = None
        if email_enc:
            user = User.objects.filter(email_cipher=email_enc).first()
        if not user and phone_enc:
            user = User.objects.filter(phone_cipher=phone_enc).first()

        is_new = user is None
        if is_new:
            user = User.objects.create_user(
                email_cipher=email_enc,
                phone_cipher=phone_enc,
                role='student'
            )

        self._sync_vk_profile(user, vk_user, is_new=is_new)

        return Response(get_tokens_for_user(user), status=200)