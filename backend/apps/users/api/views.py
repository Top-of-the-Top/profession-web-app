from django.utils import timezone
import os
import hashlib
from django.core.cache import cache
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
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
)
from .utils.crypto_utils import encrypt_data
from .utils.notification_utils import (
    send_reset_password_email,
    send_reset_password_sms,
    send_verification_email,
    send_verification_sms,
)
from .utils.registration_utils import (
    check_contact_rate_limit,
    generate_registration_code,
    verify_registration_code,
)
from .utils.token_utils import get_tokens_for_user, set_reset_token
from .utils.verification_utils import (
    generate_verification_code_for_user,
    verify_code,
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
                status = status.HTTP_200_OK,
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
                status = status.HTTP_200_OK,
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
            200: {"description": "Ссылка или код отправлены.", "schema": {"type": "object", "properties": {"status": {"type": "string", "example": "success"}}}},
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
            200: {"description": "Профиль обновлён.", "schema": {"type": "object", "properties": {"status": {"type": "string", "example": "success"}}}},
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
        if 'avatar' in data:
            profile.avatar = data['avatar']
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
    