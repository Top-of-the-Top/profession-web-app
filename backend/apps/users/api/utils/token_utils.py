import secrets
from datetime import datetime, timedelta, timezone

from django.utils import timezone as django_timezone
from rest_framework_simplejwt.tokens import RefreshToken


def generate_reset_token():
    return secrets.token_urlsafe(32)


def set_reset_token(user, valid_hours=24):
    user.reset_token = generate_reset_token()
    user.reset_token_expires = django_timezone.now() + timedelta(hours=valid_hours)
    user.save(update_fields=["reset_token", "reset_token_expires"])
    return user.reset_token


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    user_role = getattr(user, "role", "student")
    refresh["role"] = user_role
    access["role"] = user_role

    return {
        "access_token": str(access),
        "access_expires_at": datetime.fromtimestamp(access["exp"], tz=timezone.utc).isoformat(),
        "refresh_token": str(refresh),
        "refresh_expires_at": datetime.fromtimestamp(refresh["exp"], tz=timezone.utc).isoformat(),
        "role": user_role,
    }
