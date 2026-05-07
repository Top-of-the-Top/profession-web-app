import hashlib
import hmac
import secrets
from datetime import datetime

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.utils import timezone as django_timezone

from ..constants import (
    MSG_CODE_EXPIRED,
    MSG_CODE_INVALID,
    MSG_CODE_NOT_FOUND,
    MSG_TOO_MANY_ATTEMPTS,
)
from ..errors import VerificationError
from .crypto_utils import encrypt_data
from .verification_utils import MAX_VERIFY_ATTEMPTS


def generate_registration_code(contact, password, contact_type="phone"):
    code = f"{secrets.randbelow(1000000):06d}"
    contact_cipher = encrypt_data(contact)
    cache_key = f"pending_registration_{contact_type}_{contact_cipher}"

    data = {
        "code": code,
        "contact": contact,
        "contact_type": contact_type,
        "password_hash": make_password(password),
        "created_at": django_timezone.now().isoformat(),
    }

    cache.set(cache_key, data, timeout=300)
    return code


def verify_registration_code(contact, user_code, contact_type):
    contact_cipher = encrypt_data(contact)
    cache_key = f"pending_registration_{contact_type}_{contact_cipher}"
    data = cache.get(cache_key)

    if not data:
        raise VerificationError("not_found", MSG_CODE_NOT_FOUND)

    attempts_key = f"reg_verify_attempts_{contact_type}_{contact_cipher}"
    attempts = cache.get(attempts_key, 0)

    if attempts >= MAX_VERIFY_ATTEMPTS:
        cache.delete(cache_key)
        cache.delete(attempts_key)
        raise VerificationError("too_many_attempts", MSG_TOO_MANY_ATTEMPTS)

    created_at = data.get("created_at")
    if created_at:
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elapsed = (django_timezone.now() - created_at).total_seconds()
        if elapsed > 300:
            cache.delete(cache_key)
            cache.delete(attempts_key)
            raise VerificationError("expired", MSG_CODE_EXPIRED)

    if not hmac.compare_digest(data["code"], user_code):
        cache.set(attempts_key, attempts + 1, timeout=300)
        raise VerificationError("invalid", MSG_CODE_INVALID)

    cache.delete(cache_key)
    cache.delete(attempts_key)
    return {
        "contact": data["contact"],
        "contact_type": data["contact_type"],
        "password_hash": data["password_hash"],
    }


def check_contact_rate_limit(contact, contact_type="phone"):
    contact_hash = hashlib.sha256(contact.encode()).hexdigest()[:16]
    rate_key = f"rate_{contact_type}_{contact_hash}"

    if cache.get(rate_key):
        try:
            ttl = cache.ttl(rate_key)
            retry_after = ttl if ttl and ttl > 0 else 60
        except AttributeError:
            retry_after = 60

        return False, retry_after

    cache.set(rate_key, 1, timeout=60)
    return True, 0
