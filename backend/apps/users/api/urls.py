from django.urls import path
from .views import (
  RegisterView, VerifyRegisterView, LoginView, RefreshTokenView,
  ResetPasswordView, RecoverPasswordPhoneView, RecoverPasswordView, 
  ProfileView, VerifyEmailChangeView, VerifyPhoneChangeView
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
    path('profile/verify-email/', VerifyEmailChangeView.as_view(), name='verify-email'),
    path('profile/verify-phone/', VerifyPhoneChangeView.as_view(), name='verify-phone'),
]
