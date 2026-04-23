import hmac
import secrets
from datetime import datetime

from django.core.cache import cache
from django.utils import timezone as django_timezone

from ..constants import MSG_CODE_EXPIRED, MSG_CODE_INVALID, MSG_CODE_NOT_FOUND
from ..errors import VerificationError

MAX_VERIFY_ATTEMPTS = 5


def generate_verification_code_for_user(user_id, contact_type, new_contact):
    code = f"{secrets.randbelow(1000000):06d}"
    cache_key = f'verification_code_{user_id}_{contact_type}'

    data = {
        'code': code,
        'new_contact': new_contact,
        'created_at': django_timezone.now().isoformat()
    }

    cache.set(cache_key, data, timeout=300)

    return code


def get_verification_code_for_user(user_id, contact_type):
    cache_key = f'verification_code_{user_id}_{contact_type}'
    return cache.get(cache_key)


def delete_verification_code(user_id: int, contact_type: str):
    cache_key = f"verification_code_{user_id}_{contact_type}"
    cache.delete(cache_key)


def verify_code(user_id, contact_type, user_code):
    data = get_verification_code_for_user(user_id, contact_type)

    if not data:
        raise VerificationError('not_found', MSG_CODE_NOT_FOUND)

    attempts_key = f'verify_attempts_{user_id}_{contact_type}'
    attempts = cache.get(attempts_key, 0)

    if attempts >= MAX_VERIFY_ATTEMPTS:
        delete_verification_code(user_id, contact_type)
        cache.delete(attempts_key)
        raise VerificationError(
            'too_many_attempts',
            'Слишком много попыток. Запросите новый код.'
        )

    created_at = data.get('created_at')
    if created_at:
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elapsed = (django_timezone.now() - created_at).total_seconds()
        if elapsed > 300:
            delete_verification_code(user_id, contact_type)
            cache.delete(attempts_key)
            raise VerificationError('expired', MSG_CODE_EXPIRED)

    if not hmac.compare_digest(data['code'], user_code):
        cache.set(attempts_key, attempts + 1, timeout=300)
        raise VerificationError('invalid', MSG_CODE_INVALID)

    delete_verification_code(user_id, contact_type)
    cache.delete(attempts_key)
    return data['new_contact']
