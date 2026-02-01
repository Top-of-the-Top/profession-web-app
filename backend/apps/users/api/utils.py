from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timezone, timedelta
import secrets
from django.utils import timezone


def generate_reset_token():
  return secrets.token_urlsafe(32)


def set_reset_token(user, valid_hours=24):
  user.reset_token = generate_reset_token()
  user.reset_token_expires = timezone.now() + timedelta(hours=valid_hours)
  user.save(update_fields=['reset_token', 'reset_token_expires'])
  return user.reset_token


def get_tokens_for_user(user):
  refresh = RefreshToken.for_user(user)
  access = refresh.access_token
  return {
    'access_token': str(refresh.access_token),
    'access_expires_at': datetime.fromtimestamp(access['exp'], tz=timezone.utc).isoformat(),
    'refresh_token': str(refresh),
    'refresh_expires_at': datetime.fromtimestamp(refresh['exp'], tz=timezone.utc).isoformat(),
  }
