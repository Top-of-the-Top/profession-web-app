from django.urls import path
from .views import *

app_name = 'users'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/register/verify/', VerifyRegisterView.as_view(), name='register_verify'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('auth/reset/', ResetPasswordView.as_view(), name='reset'),
    path('auth/recover/set/', RecoverPasswordView.as_view(), name='recover_set'),
    path('auth/recover/phone/', RecoverPasswordPhoneView.as_view(), name='recover_phone'),
    path('app/profile/', ProfileView.as_view(), name='profile'),
    path('app/profile/verify_email/', VerifyEmailChangeView.as_view(), name='verify_email'),
    path('app/profile/verify_phone/', VerifyPhoneChangeView.as_view(), name='verify_phone'),
]
