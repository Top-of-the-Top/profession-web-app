from django.urls import path
from .views import (
    RegisterView, VerifyRegisterView, LoginView, RefreshTokenView,
    ResetPasswordView, RecoverPasswordPhoneView, RecoverPasswordView,
    ProfileView, VerifyEmailChangeView, VerifyPhoneChangeView,
    AvatarView,
    YandexCallbackAPIView, YandexOauth2APIView,
    VKCallbackAPIView, VKOAauth2APIView,
)

app_name = 'users'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/register/verify/', VerifyRegisterView.as_view(), name='register-verify'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    path('auth/reset/', ResetPasswordView.as_view(), name='reset'),
    path('auth/recover/set/', RecoverPasswordView.as_view(), name='recover_set'),
    path('auth/recover/phone/', RecoverPasswordPhoneView.as_view(), name='recover-phone'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/avatar/', AvatarView.as_view(), name='profile-avatar'),
    path('profile/verify-email/', VerifyEmailChangeView.as_view(), name='verify-email'),
    path('profile/verify-phone/', VerifyPhoneChangeView.as_view(), name='verify-phone'),
    path('auth/yandex/callback/', YandexCallbackAPIView.as_view(), name='yandex-callback'),
    path('auth/vk/callback/', VKCallbackAPIView.as_view(), name='vk-callback'),
    path('auth/yandex/exchange/', YandexOauth2APIView.as_view(), name='yandex-exchange'),
    path('auth/vk/exchange/', VKOAauth2APIView.as_view(), name='vk-exchange'),
]
