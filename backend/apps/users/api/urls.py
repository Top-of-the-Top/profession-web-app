from django.urls import path
from .views import *

app_name = 'users'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('auth/reset/', ResetPasswordView.as_view(), name='reset'),
    path('auth/recover/set/', RecoverPasswordView.as_view(), name='recover_set'),
    path('app/profile/', ProfileView.as_view(), name='profile'),
]
