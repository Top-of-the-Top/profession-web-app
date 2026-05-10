import hashlib
import logging
import os
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.serializers import ServiceErrorResponseSerializer
from apps.core.processors.error_processor import process_error_response

from ..models import Profile, User
from .errors import (
    AvatarBindFailed,
    ContactRequired,
    EmailAlreadyExists,
    EmailSendFailed,
    OAuthInvalidCode,
    OAuthInvalidRequest,
    OAuthInvalidState,
    OAuthMissingProfileData,
    OAuthProviderUnavailable,
    PhoneAlreadyExists,
    RateLimitExceeded,
    RefreshTokenInvalid,
    RefreshTokenMissing,
    ResetTokenInvalid,
    ResetTokenMissing,
    SmsSendFailed,
    UserNotFound,
    ValidationFailed,
    VerificationError,
)
from .serializers import (
    CodeSentResponseSerializer,
    DetailOnlyResponseSerializer,
    EmailRegisterSerializer,
    LoginSerializer,
    PhoneRegisterSerializer,
    RateLimitedResponseSerializer,
    RecoverPasswordPhoneSerializer,
    RecoverPasswordRequestSerializer,
    RefreshTokenRequestSerializer,
    RegisterSerializer,
    ResetPasswordPhoneTokenResponseSerializer,
    ResetPasswordRequestSerializer,
    ResetPasswordSuccessSerializer,
    SimpleStatusResponseSerializer,
    TokenResponseSerializer,
    UpdateProfileSerializer,
    UserProfileSerializer,
    VerifyCodeSerializer,
    VerifyRegisterSerializer,
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
from .utils.verification_utils import generate_verification_code_for_user, verify_code

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300

SCHEMA_401 = {"type": "object", "properties": {"detail": {"type": "string"}}}
SCHEMA_VALIDATION_ERROR = {"type": "object", "description": "Объект с ошибками валидации по полям."}

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Регистрация",
        description=(
            "Первый шаг двухэтапной регистрации. "
            "Передайте email или номер телефона — на него придёт код подтверждения. "
            "Для подтверждения используйте POST /verify-register/."
        ),
        tags=["Users"],
        request=RegisterSerializer,
        responses={
            200: CodeSentResponseSerializer,
            403: DetailOnlyResponseSerializer,
            429: RateLimitedResponseSerializer,
        },
    )
    def post(self, request):
        email = (request.data.get("email") or "").strip()
        phone = (request.data.get("phone_number") or "").strip()

        if not email and not phone:
            return process_error_response(ContactRequired())

        if phone and not email:
            serializer = PhoneRegisterSerializer(data=request.data)
            if not serializer.is_valid():
                return process_error_response(ValidationFailed(serializer.errors))

            phone_number = serializer.validated_data["phone_number"]
            password = serializer.validated_data["password"]

            is_allowed, retry_after = check_contact_rate_limit(phone_number, "phone")
            if not is_allowed:
                return process_error_response(RateLimitExceeded(retry_after))

            code = generate_registration_code(phone_number, password, contact_type="phone")
            send_verification_sms(phone_number, code)
            return Response(
                {"status": "code_sent", "detail": "Код подтверждения отправлен на телефон."}
            )

        if email:
            serializer = EmailRegisterSerializer(data=request.data)
            if not serializer.is_valid():
                return process_error_response(ValidationFailed(serializer.errors))

            email_value = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            is_allowed, retry_after = check_contact_rate_limit(email_value, "email")
            if not is_allowed:
                return process_error_response(RateLimitExceeded(retry_after))

            code = generate_registration_code(email_value, password, contact_type="email")
            send_verification_email(email_value, code)
            return Response(
                {"status": "code_sent", "detail": "Код подтверждения отправлен на почту."}
            )


class VerifyRegisterView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Подтверждение регистрации",
        description=(
            "Второй шаг регистрации. Передайте код из SMS или письма вместе с email или phone_number. "
            "При успехе возвращаются JWT-токены."
        ),
        tags=["Users"],
        request=VerifyRegisterSerializer,
        responses={
            200: TokenResponseSerializer,
            400: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = VerifyRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return process_error_response(ValidationFailed(serializer.errors))

        phone = (serializer.validated_data.get("phone_number") or "").strip()
        email = (serializer.validated_data.get("email") or "").strip()
        user_code = serializer.validated_data["code"]

        contact = phone if phone else email
        contact_type = "phone" if phone else "email"

        try:
            reg_data = verify_registration_code(contact, user_code, contact_type)
        except VerificationError as e:
            return process_error_response(e)

        if reg_data["contact_type"] == "phone":
            user = User.objects.create_user(phone_cipher=encrypt_data(reg_data["contact"]))
        else:
            user = User.objects.create_user(email_cipher=encrypt_data(reg_data["contact"]))

        user.password = reg_data["password_hash"]
        user.save(update_fields=["password"])

        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Вход",
        description=(
            "Аутентификация по email или phone_number и паролю. "
            "После 5 неудачных попыток вход блокируется на 5 минут. "
            "При успехе возвращаются access и refresh токены."
        ),
        tags=["Users"],
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            400: SCHEMA_VALIDATION_ERROR,
            429: RateLimitedResponseSerializer,
        },
    )
    def post(self, request):
        email = (request.data.get("email") or "").strip()
        phone = (request.data.get("phone_number") or "").strip()
        contact = email or phone

        if contact:
            contact_hash = hashlib.sha256(contact.encode()).hexdigest()[:16]
            lockout_key = f"login_lockout_{contact_hash}"
            attempts_key = f"login_attempts_{contact_hash}"

            if cache.get(lockout_key):
                ttl = getattr(cache, "ttl", lambda k: LOGIN_LOCKOUT_SECONDS)(lockout_key)
                return process_error_response(RateLimitExceeded(ttl))

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            if contact:
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=LOGIN_LOCKOUT_SECONDS)
                if attempts >= MAX_LOGIN_ATTEMPTS:
                    cache.set(lockout_key, 1, timeout=LOGIN_LOCKOUT_SECONDS)
                    cache.delete(attempts_key)
            return process_error_response(ValidationFailed(serializer.errors))

        if contact:
            cache.delete(attempts_key)

        return Response(
            get_tokens_for_user(serializer.validated_data["user"]), status=status.HTTP_200_OK
        )


class RefreshTokenView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Обновление токенов",
        description="Принимает действующий refresh_token и выдаёт новую пару access/refresh токенов.",
        tags=["Users"],
        request=RefreshTokenRequestSerializer,
        responses={
            200: TokenResponseSerializer,
            401: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return process_error_response(RefreshTokenMissing())
        try:
            refresh = RefreshToken(refresh_token)
            user = User.objects.get(id=refresh["user_id"])
            return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)
        except Exception:
            return process_error_response(RefreshTokenInvalid())


class ResetPasswordView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Запрос на сброс пароля",
        description=(
            "Передайте email или phone_number. "
            "На email отправляется ссылка для сброса, на телефон — SMS-код. "
            "Для завершения через email используйте PATCH /recover/, "
            "через телефон — сначала POST /recover-phone/, затем PATCH /recover/."
        ),
        tags=["Users"],
        request=ResetPasswordRequestSerializer,
        responses={
            200: ResetPasswordSuccessSerializer,
            403: ServiceErrorResponseSerializer,
            429: RateLimitedResponseSerializer,
            500: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        email = (request.data.get("email") or "").strip()
        phone = (request.data.get("phone_number") or "").strip()

        if not email and not phone:
            return process_error_response(ContactRequired())

        user = None
        if email:
            user = User.objects.filter(email_cipher=encrypt_data(email)).first()
        if not user and phone:
            user = User.objects.filter(phone_cipher=encrypt_data(phone)).first()
        if not user:
            return process_error_response(UserNotFound())

        if email:
            token = set_reset_token(user)
            recover_url = f"{os.environ.get('FRONTEND_HOST')}/recover?token={token}"
            ok, _ = send_reset_password_email(email, recover_url)
            if not ok:
                return process_error_response(EmailSendFailed())
            return Response({"status": "success"}, status=status.HTTP_200_OK)

        is_allowed, retry_after = check_contact_rate_limit(phone, "phone")
        if not is_allowed:
            return process_error_response(RateLimitExceeded(retry_after))

        code = generate_verification_code_for_user(
            user_id=user.id, contact_type="reset_phone", new_contact=phone
        )
        ok, _ = send_reset_password_sms(phone, code)
        if not ok:
            return process_error_response(SmsSendFailed())

        return Response(
            {"status": "success", "detail": "Код для сброса пароля отправлен на телефон."},
            status=status.HTTP_200_OK,
        )


class RecoverPasswordView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Установка нового пароля",
        description=(
            "Завершение сброса пароля по токену из письма или из POST /recover-phone/. "
            "При успехе возвращаются JWT-токены — пользователь сразу авторизован."
        ),
        tags=["Users"],
        request=RecoverPasswordRequestSerializer,
        responses={
            200: TokenResponseSerializer,
            403: ServiceErrorResponseSerializer,
        },
    )
    def patch(self, request):
        token = request.data.get("token")
        password = request.data.get("password")
        if not token or not password:
            return process_error_response(ResetTokenMissing())

        user = User.objects.filter(
            reset_token=token, reset_token_expires__gt=timezone.now()
        ).first()
        if not user:
            return process_error_response(ResetTokenInvalid())

        user.set_password(password)
        user.reset_token = ""
        user.reset_token_expires = None
        user.save(update_fields=["password", "reset_token", "reset_token_expires"])
        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)


class RecoverPasswordPhoneView(APIView):
    permission_classes = []

    @extend_schema(
        summary="Проверка SMS-кода для сброса пароля",
        description=(
            "Передайте phone_number и 6-значный код из SMS. "
            "При успехе возвращается reset_token, который нужно передать в PATCH /recover/."
        ),
        tags=["Users"],
        request=RecoverPasswordPhoneSerializer,
        responses={
            200: ResetPasswordPhoneTokenResponseSerializer,
            400: ServiceErrorResponseSerializer,
            403: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = RecoverPasswordPhoneSerializer(data=request.data)
        if not serializer.is_valid():
            return process_error_response(ValidationFailed(serializer.errors))

        phone_number = serializer.validated_data["phone_number"].strip()
        user_code = serializer.validated_data["code"]

        user = User.objects.filter(phone_cipher=encrypt_data(phone_number)).first()
        if not user:
            return process_error_response(UserNotFound())

        try:
            verify_code(user_id=user.id, contact_type="reset_phone", user_code=user_code)
        except VerificationError as e:
            return process_error_response(e)

        return Response({"token": set_reset_token(user)}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Получить профиль",
        description="Возвращает профиль текущего авторизованного пользователя.",
        tags=["Users"],
        responses={
            200: UserProfileSerializer,
            401: {"schema": SCHEMA_401},
        },
    )
    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        class UserProfileWrapper:
            def __init__(self, user, profile):
                self.user = user
                self.profile = profile

        return Response(
            UserProfileSerializer(
                UserProfileWrapper(user, profile), context={"request": request}
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Обновить профиль",
        description=(
            "Частичное обновление профиля. "
            "При смене email или phone_number на указанный контакт отправляется код подтверждения — "
            "изменение применяется только после верификации через POST /verify-email/ или /verify-phone/."
        ),
        tags=["Users"],
        request=UpdateProfileSerializer,
        responses={
            200: SimpleStatusResponseSerializer,
            400: SCHEMA_VALIDATION_ERROR,
            401: {"schema": SCHEMA_401},
            403: ServiceErrorResponseSerializer,
            404: ServiceErrorResponseSerializer,
            409: ServiceErrorResponseSerializer,
            429: RateLimitedResponseSerializer,
            503: ServiceErrorResponseSerializer,
        },
    )
    def patch(self, request):
        user = request.user
        serializer = UpdateProfileSerializer(data=request.data, context={"user": user})
        if not serializer.is_valid():
            return process_error_response(ValidationFailed(serializer.errors))
        data = serializer.validated_data
        profile, _ = Profile.objects.get_or_create(user=user)

        if "email" in data and data["email"]:
            code = generate_verification_code_for_user(
                user_id=user.id, contact_type="email", new_contact=data["email"]
            )
            send_verification_email(data["email"], code)

        if "phone_number" in data and data["phone_number"]:
            is_allowed, retry_after = check_contact_rate_limit(data["phone_number"], "phone")
            if not is_allowed:
                return process_error_response(RateLimitExceeded(retry_after))
            code = generate_verification_code_for_user(
                user_id=user.id, contact_type="phone", new_contact=data["phone_number"]
            )
            send_verification_sms(data["phone_number"], code)

        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        user.save()

        if "gender" in data:
            profile.gender = data["gender"]
        if "birthday" in data:
            profile.birthday = data["birthday"]
        profile.save()

        if "avatar_asset_id" in data:
            from django.contrib.contenttypes.models import ContentType

            from apps.core.meta_management.errors import AssetError
            from apps.core.meta_management.factory import build_binding_api
            from apps.core.models import AssetUsage

            try:
                build_binding_api().sync_single(
                    content_object=profile,
                    role="user_avatar",
                    asset_id=data["avatar_asset_id"],
                    owner=user,
                )
            except AssetError as exc:
                return process_error_response(exc)

            bound = AssetUsage.objects.filter(
                content_type=ContentType.objects.get_for_model(profile),
                object_id=str(profile.pk),
                role="user_avatar",
                asset_id=data["avatar_asset_id"],
            ).exists()
            if data["avatar_asset_id"] is not None and not bound:
                return process_error_response(
                    AvatarBindFailed(details={"asset_id": str(data["avatar_asset_id"])})
                )

        return Response({"status": "success"}, status=status.HTTP_200_OK)


class VerifyEmailChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Подтверждение смены email",
        description=(
            "После PATCH /profile/ с новым email на почту отправляется 6-значный код. "
            "Передайте его сюда — email будет обновлён."
        ),
        tags=["Users"],
        request=VerifyCodeSerializer,
        responses={
            200: SimpleStatusResponseSerializer,
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_401},
        },
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return process_error_response(ValidationFailed(serializer.errors))

        try:
            new_email = verify_code(
                user_id=request.user.id,
                contact_type="email",
                user_code=serializer.validated_data["code"],
            )
        except VerificationError as e:
            return process_error_response(e)

        new_cipher = encrypt_data(new_email)
        if User.objects.filter(email_cipher=new_cipher).exclude(pk=request.user.pk).exists():
            return process_error_response(EmailAlreadyExists())

        request.user.email_cipher = new_cipher
        try:
            request.user.save(update_fields=["email_cipher"])
        except IntegrityError:
            return process_error_response(EmailAlreadyExists())

        return Response({"status": "success"}, status=status.HTTP_200_OK)


class VerifyPhoneChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Подтверждение смены телефона",
        description=(
            "После PATCH /profile/ с новым номером на телефон приходит SMS с кодом. "
            "Передайте 6-значный код — номер будет обновлён."
        ),
        tags=["Users"],
        request=VerifyCodeSerializer,
        responses={
            200: SimpleStatusResponseSerializer,
            400: ServiceErrorResponseSerializer,
            401: {"schema": SCHEMA_401},
        },
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return process_error_response(ValidationFailed(serializer.errors))

        try:
            new_phone = verify_code(
                user_id=request.user.id,
                contact_type="phone",
                user_code=serializer.validated_data["code"],
            )
        except VerificationError as e:
            return process_error_response(e)

        new_cipher = encrypt_data(new_phone)
        if User.objects.filter(phone_cipher=new_cipher).exclude(pk=request.user.pk).exists():
            return process_error_response(PhoneAlreadyExists())

        request.user.phone_cipher = new_cipher
        try:
            request.user.save(update_fields=["phone_cipher"])
        except IntegrityError:
            return process_error_response(PhoneAlreadyExists())

        return Response({"status": "success"}, status=status.HTTP_200_OK)


class YandexCallbackAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Callback для Яндекс OAuth",
        description=(
            "Принимает code и state от Яндекса после авторизации пользователя. "
            "Сохраняет state в кэш и перенаправляет на фронтенд для завершения входа."
        ),
        tags=["Users"],
        parameters=[
            OpenApiParameter("code", OpenApiTypes.STR, description="Код авторизации"),
            OpenApiParameter("state", OpenApiTypes.STR, description="CSRF-токен для валидации"),
            OpenApiParameter(
                "error", OpenApiTypes.STR, description="Код ошибки (если авторизация отклонена)"
            ),
            OpenApiParameter(
                "error_description", OpenApiTypes.STR, description="Текстовое описание ошибки"
            ),
        ],
        responses={302: None},
    )
    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        params = {"provider": "yandex"}

        if code:
            cache.set(f"oauth:yandex:state:{state}", 1, timeout=600)
            params.update({"code": code, "state": state})
        elif error:
            params.update(
                {
                    "error": error,
                    "error_description": request.query_params.get("error_description", ""),
                }
            )
            if state:
                params["state"] = state
        else:
            params["error"] = "invalid_callback_payload"

        return HttpResponseRedirect(
            f"{settings.FRONTEND_OAUTH_YANDEX_REDIRECT_URI}?{urlencode(params)}"
        )


class YandexOauth2APIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Авторизация через Яндекс",
        description=(
            "Обменивает code и state от Яндекс OAuth на JWT-токены платформы. "
            "Если пользователь с таким email или телефоном не найден — создаётся автоматически."
        ),
        tags=["Users"],
        request={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Код авторизации от Яндекс OAuth"},
                "state": {"type": "string", "description": "CSRF-токен, выданный при старте OAuth"},
            },
            "required": ["code", "state"],
        },
        responses={
            200: TokenResponseSerializer,
            400: ServiceErrorResponseSerializer,
            502: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        code = request.data.get("code")
        state = request.data.get("state")

        if not code or not state:
            return process_error_response(OAuthInvalidRequest())

        if not self._validate_state(state):
            return process_error_response(OAuthInvalidState())

        try:
            yandex_tokens = self._exchange_code_for_token(code)
        except OAuthProviderUnavailable as e:
            return process_error_response(e)
        if not yandex_tokens:
            return process_error_response(OAuthInvalidCode())

        user_info = self._get_yandex_user_info(yandex_tokens["access_token"])
        email = user_info.get("default_email")
        default_phone = user_info.get("default_phone") or {}
        phone = default_phone.get("number") if isinstance(default_phone, dict) else None

        if not email and not phone:
            return process_error_response(OAuthMissingProfileData())

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
                email_cipher=email_enc, phone_cipher=phone_enc, role="student"
            )

        self._sync_user_profile(user, user_info, is_new=is_new)
        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)

    def _validate_state(self, state):
        return bool(cache.delete(f"oauth:yandex:state:{state}"))

    def _exchange_code_for_token(self, code):
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.YANDEX_CLIENT_ID,
            "client_secret": settings.YANDEX_CLIENT_SECRET,
        }
        try:
            response = httpx.post("https://oauth.yandex.ru/token", data=data, timeout=5.0)
            return response.json() if response.status_code == 200 else None
        except httpx.RequestError as e:
            logger.exception("Yandex exchange network error: %s", e)
            raise OAuthProviderUnavailable()

    def _get_yandex_user_info(self, token):
        try:
            resp = httpx.get(
                "https://login.yandex.ru/info?format=json",
                headers={"Authorization": f"OAuth {token}"},
                timeout=5.0,
            )
            return resp.json() if resp.status_code == 200 else {}
        except httpx.RequestError:
            return {}

    def _sync_user_profile(self, user, user_info, *, is_new):
        user_fields = []
        first_name = (user_info.get("first_name") or "").strip()
        last_name = (user_info.get("last_name") or "").strip()

        if first_name and (is_new or not user.first_name):
            user.first_name = first_name
            user_fields.append("first_name")
        if last_name and (is_new or not user.last_name):
            user.last_name = last_name
            user_fields.append("last_name")
        if user_fields:
            user.save(update_fields=user_fields)

        profile, _ = Profile.objects.get_or_create(user=user)
        profile_fields = []

        birthday_raw = user_info.get("birthday")
        if birthday_raw and (is_new or not profile.birthday):
            from datetime import date

            try:
                parsed = date.fromisoformat(birthday_raw)
                if parsed.year > 0:
                    profile.birthday = parsed
                    profile_fields.append("birthday")
            except (ValueError, AttributeError):
                pass

        sex = user_info.get("sex")
        if sex and (is_new or not profile.gender):
            mapped = {"male": "М", "female": "Ж"}.get(sex)
            if mapped:
                profile.gender = mapped
                profile_fields.append("gender")

        if profile_fields:
            profile.save(update_fields=profile_fields)


class VKCallbackAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Callback для ВКонтакте OAuth",
        description=(
            "Принимает данные от VK ID после авторизации. "
            "Пробрасывает code, state и обязательный device_id на фронтенд через редирект."
        ),
        tags=["Users"],
        parameters=[
            OpenApiParameter("code", OpenApiTypes.STR, description="Код авторизации"),
            OpenApiParameter("state", OpenApiTypes.STR, description="CSRF-токен"),
            OpenApiParameter("device_id", OpenApiTypes.STR, description="Идентификатор устройства"),
            OpenApiParameter("error", OpenApiTypes.STR, description="Код ошибки"),
        ],
        responses={302: None},
    )
    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        device_id = request.query_params.get("device_id")
        error = request.query_params.get("error")

        params = {"provider": "vk"}

        if code:
            cache.set(f"oauth:vk:state:{state}", 1, timeout=600)
            params.update({"code": code, "state": state, "device_id": device_id})
        elif error:
            params.update(
                {
                    "error": error,
                    "error_description": request.query_params.get("error_description", ""),
                }
            )
            if state:
                params["state"] = state
        else:
            params["error"] = "invalid_callback_payload"

        return HttpResponseRedirect(
            f"{settings.FRONTEND_OAUTH_VK_REDIRECT_URI}?{urlencode(params)}"
        )


class VKOAauth2APIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Авторизация через ВКонтакте",
        description=(
            "Обменивает code, state, code_verifier и device_id от VK OAuth на JWT-токены платформы. "
            "Если пользователь не найден — создаётся автоматически."
        ),
        tags=["Users"],
        request={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Код авторизации от VK OAuth"},
                "state": {"type": "string", "description": "CSRF-токен, выданный при старте OAuth"},
                "code_verifier": {"type": "string", "description": "PKCE code_verifier"},
                "device_id": {
                    "type": "string",
                    "description": "Идентификатор устройства из VK SDK",
                },
            },
            "required": ["code", "state", "code_verifier", "device_id"],
        },
        responses={
            200: TokenResponseSerializer,
            400: ServiceErrorResponseSerializer,
            502: ServiceErrorResponseSerializer,
        },
    )
    def post(self, request):
        code = request.data.get("code")
        state = request.data.get("state")
        code_verifier = request.data.get("code_verifier")
        device_id = request.data.get("device_id")

        if not all([code, state, code_verifier, device_id]):
            return process_error_response(OAuthInvalidRequest())

        if not self._validate_state(state):
            return process_error_response(OAuthInvalidState())

        try:
            vk_tokens = self._exchange_code_for_tokens(code, code_verifier, device_id)
        except OAuthProviderUnavailable as e:
            return process_error_response(e)
        if not vk_tokens or "access_token" not in vk_tokens:
            return process_error_response(OAuthInvalidCode())

        user_info = self._get_vk_user_info(vk_tokens["access_token"])
        vk_user = user_info.get("user", {})
        email = vk_user.get("email")
        phone = vk_user.get("phone")

        if not email and not phone:
            return process_error_response(OAuthMissingProfileData())

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
                email_cipher=email_enc, phone_cipher=phone_enc, role="student"
            )

        self._sync_vk_profile(user, vk_user, is_new=is_new)
        return Response(get_tokens_for_user(user), status=status.HTTP_200_OK)

    def _validate_state(self, state):
        return bool(cache.delete(f"oauth:vk:state:{state}"))

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
                logger.error(
                    "VK exchange failed: status=%s body=%s", response.status_code, response.text
                )
                return None
            return response.json()
        except httpx.RequestError as e:
            logger.exception("VK exchange network error: %s", e)
            raise OAuthProviderUnavailable()

    def _get_vk_user_info(self, access_token):
        try:
            resp = httpx.post(
                "https://id.vk.ru/oauth2/user_info",
                data={"access_token": access_token, "client_id": settings.VK_CLIENT_ID},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if "error" not in data else {}
            return {}
        except httpx.RequestError as e:
            logger.exception("VK user info error: %s", e)
            return {}

    def _sync_vk_profile(self, user, vk_user, *, is_new):
        user_fields = []
        first_name = vk_user.get("first_name", "").strip()
        last_name = vk_user.get("last_name", "").strip()

        if first_name and (is_new or not user.first_name):
            user.first_name = first_name
            user_fields.append("first_name")
        if last_name and (is_new or not user.last_name):
            user.last_name = last_name
            user_fields.append("last_name")
        if user_fields:
            user.save(update_fields=user_fields)

        profile, _ = Profile.objects.get_or_create(user=user)
        vk_sex = vk_user.get("sex")
        if vk_sex and (is_new or not profile.gender):
            profile.gender = "М" if vk_sex == 2 else "Ж"
        profile.save()
