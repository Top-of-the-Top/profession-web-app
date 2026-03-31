from django.utils import timezone
import os
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .errors import VerificationError
from ..models import User, Profile
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    UpdateProfileSerializer,
    TokenResponseSerializer,
    VerifyCodeSerializer,
)
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
)
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

SCHEMA_401 = {
    "type": "object",
    "properties": {"detail": {"type": "string", "description": "Токен/учётные данные отсутствуют или недействительны."}},
}
SCHEMA_403 = {
    "type": "object",
    "properties": {"detail": {"type": "string", "description": "Сообщение об ошибке (отказ в действии, не аутентификация)."}},
}
SCHEMA_VALIDATION_ERROR = {
    "type": "object",
    "description": "Объект с ошибками валидации: ключи — имена полей, значения — список строк ошибок.",
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
            "Создаёт нового пользователя по email и/или номеру телефона и паролю. "
            "Передайте в теле запроса либо email, либо phone_number (или оба), а также password (не менее 8 символов). "
            "При успехе возвращается объект с access_token, access_expires_at, refresh_token, refresh_expires_at — эти токены используются для доступа к защищённым эндпоинтам (заголовок Authorization: Bearer <access_token>). "
            "При ошибке валидации (дубликат email/телефона, не указан контакт, короткий пароль) возвращается 403 и объект с полями-ошибками."
        ),
        tags=["Users"],
        request=RegisterSerializer,
        responses={
            200: TokenResponseSerializer,
            403: {"description": "Валидация: дубликат email/phone или не указан контакт. Тело — объект с полями ошибок.", "schema": SCHEMA_VALIDATION_ERROR},
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_403_FORBIDDEN
            )
        data = serializer.validated_data
        email_cipher = data.get('email_cipher') or None
        phone_cipher = data.get('phone_cipher') or None
        password = data['password']

        user = User.objects.create_user(
            email_cipher=email_cipher,
            phone_cipher=phone_cipher,
            password=password
        )

        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Вход пользователя",
        description=(
            "Аутентификация по email и/или номеру телефона и паролю. "
            "В теле запроса передайте email или phone_number (или оба) и password. "
            "При успехе возвращается объект с access_token, access_expires_at, refresh_token, refresh_expires_at. "
            "При неверной паре контакт/пароль или отсутствии контакта возвращается 403 и объект с ошибками валидации."
        ),
        tags=["Users"],
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            400: {"description": "Валидация: неверная пара контакт/пароль или не указан контакт. Тело — объект с полями ошибок.", "schema": SCHEMA_VALIDATION_ERROR},
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        user = serializer.validated_data['user']
        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Обновление рефреш токена",
        description=(
            "Выдаёт новую пару access и refresh токенов по действующему refresh_token. "
            "В теле запроса передайте поле refresh_token (строка). "
            "Используйте этот эндпоинт, когда access_token истёк, чтобы не заставлять пользователя логиниться снова. "
            "При отсутствии refresh_token в теле или невалидном/истёкшем токене возвращается 401 с полем detail."
        ),
        tags=["Users"],
        responses={
            200: TokenResponseSerializer,
            401: {"description": "Нет refresh_token — «refresh_token обязателен»; иначе «Невалидный или истекший refresh_token».", "schema": SCHEMA_401},
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
            "Запрос на сброс пароля по email или номеру телефона. "
            "В теле передайте email и/или phone_number. На указанный email отправляется письмо со ссылкой для ввода нового пароля (страница восстановления на фронте). "
            "При успехе возвращается объект { status: 'success' }. "
            "Если не передан ни email, ни phone_number — 403 с сообщением «Необходимо указать email или phone_number». "
            "Если пользователь не найден — 403 «Пользователь не найден». "
            "При сбое отправки письма — 500 с полем detail."
        ),
        tags=["Users"],
        responses={
            200: {"description": "Письмо со ссылкой сброса отправлено.", "schema": {"type": "object", "properties": {"status": {"type": "string", "example": "success"}}}},
            403: {"description": "Нет email/phone — «Необходимо указать email или phone_number»; иначе «Пользователь не найден».", "schema": SCHEMA_403},
            500: {"description": "Ошибка отправки письма. Тело: { detail }.", "schema": SCHEMA_500},
        },
    )
    def post(self, request):
        email = (request.data.get('email') or '').strip()
        phone = (request.data.get('phone_number') or '').strip()

        if not email and not phone:
            return Response(
                {'detail': f'Необходимо указать email или phone_number'},
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
                {'detail': 'Пользователь не найден'},
                status=status.HTTP_403_FORBIDDEN
            )

        token = set_reset_token(user)
        frontend_host = os.environ.get('FRONTEND_HOST')
        recover_url = f"{frontend_host}/recover?token={token}"
        result = None

        if email:
            result = send_reset_password_email(email, recover_url)
            if not result:
                return Response(
                    {'detail': 'Ошибка отправки письма'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        elif phone:
            result = send_reset_password_sms(phone, recover_url)
            if not result:
                return Response(
                    {'detail': 'Ошибка отправки SMS'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        if result:
            return Response(
                {'status': 'success'},
                status=status.HTTP_200_OK
            )

        return Response(
            {'detail': f'Ошибка отправки письма: {str(email)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class RecoverPasswordView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Ввод нового пароля",
        description=(
            "Завершение сброса пароля: по одноразовому токену из письма и новому паролю обновляется пароль пользователя и выдаются токены. "
            "В теле передайте token (из ссылки в письме) и password_hash (новый пароль). "
            "При успехе возвращается объект с access_token, access_expires_at, refresh_token, refresh_expires_at. "
            "Если не переданы token или password_hash — 403 «token и password обязательны». "
            "Если токен не найден или истёк — 403 «Невалидный или истёкший токен»."
        ),
        tags=["Users"],
        responses={
            200: TokenResponseSerializer,
            403: {"description": "Нет token/password — «token и password обязательны»; иначе «Невалидный или истёкший токен».", "schema": SCHEMA_403},
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
        user.reset_token = None
        user.reset_token_expires = None
        user.save(update_fields=['password', 'reset_token', 'reset_token_expires'])

        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class ProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Получение профиля пользователя",
        description=(
            "Возвращает профиль текущего авторизованного пользователя. "
            "Требуется заголовок Authorization: Bearer <access_token>. "
            "В ответе: first_name, last_name, email, phone_number (расшифрованные при наличии), gender, birthday, avatar (URL). "
            "При отсутствии или невалидности токена возвращается 401 с полем detail."
        ),
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
        summary="Обновление профиля пользователя",
        description=(
            "Частичное обновление профиля и данных пользователя. Требуется Authorization: Bearer <access_token>. "
            "В теле можно передать любые из полей: first_name, last_name, email, phone_number, gender (Мужской/Женский), birthday, avatar (файл, макс. 5 МБ). "
            "При успехе возвращается { status: 'success' }. "
            "При ошибках валидации (дубликат email/телефона, неверный gender, слишком большой avatar) — 400 и объект с полями-ошибками. "
            "При невалидном/отсутствующем токене — 401."
        ),
        tags=["Users"],
        request=UpdateProfileSerializer,
        responses={
            200: {"description": "Профиль обновлён.", "schema": {"type": "object", "properties": {"status": {"type": "string", "example": "success"}}}},
            400: {"description": "Валидация. Тело — объект с полями ошибок.", "schema": SCHEMA_VALIDATION_ERROR},
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
    permission_classes = [IsAuthenticated]

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

        request.user.email_cipher = encrypt_data(new_email)
        request.user.save()

        return Response({'status': 'success'}, status=status.HTTP_200_OK)

class VerifyPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]

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

        request.user.phone_cipher = encrypt_data(new_phone)
        request.user.save()

        return Response({'status': 'success'}, status=status.HTTP_200_OK)