from django.core.cache import cache
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from sms import send_sms
from datetime import datetime, timezone, timedelta
import secrets
from django.utils import timezone as django_timezone
import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from django.contrib.auth.hashers import make_password
from .errors import VerificationError
from .constants import MSG_CODE_NOT_FOUND, MSG_CODE_EXPIRED, MSG_CODE_INVALID, MSG_TOO_MANY_ATTEMPTS
import secrets
import hmac

MAX_VERIFY_ATTEMPTS = 5

def generate_reset_token():
    return secrets.token_urlsafe(32)


def set_reset_token(user, valid_hours=24):
    user.reset_token = generate_reset_token()
    user.reset_token_expires = django_timezone.now() + timedelta(hours=valid_hours)
    user.save(update_fields=['reset_token', 'reset_token_expires'])
    return user.reset_token


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    user_role = getattr(user, 'role', 'student')
    refresh['role'] = user_role
    access['role'] = user_role

    return {
        'access_token': str(access),
        'access_expires_at': datetime.fromtimestamp(access['exp'], tz=timezone.utc).isoformat(),
        'refresh_token': str(refresh),
        'refresh_expires_at': datetime.fromtimestamp(refresh['exp'], tz=timezone.utc).isoformat(),
        'role': user_role,
    }


def _get_key_and_iv():
    encryption_key = os.getenv('ENCRYPTION_KEY', '')
    key_hex = (encryption_key or '').ljust(32, '0')[:32]

    try:
        key = bytes.fromhex(key_hex)
        if len(key) < 16:
            key = key.ljust(16, b'\x00')
        key = key[:16]
    except ValueError:
        key = hashlib.sha256(encryption_key.encode('utf-8')).digest()[:32]

    iv_hex = hashlib.sha256(
        (encryption_key or 'default').encode('utf-8')).hexdigest()[:32]
    iv = bytes.fromhex(iv_hex)[:16]

    return key, iv


def encrypt_data(plain_text: str) -> str:
    if not plain_text:
        return ''

    key, iv = _get_key_and_iv()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plain_text.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded)

    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_data(cipher_text: str) -> str:
    if not cipher_text:
        return ''

    try:
        key, iv = _get_key_and_iv()
        encrypted = base64.b64decode(cipher_text)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)

        return decrypted.decode('utf-8')
    except Exception:
        return ''

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
            from datetime import datetime
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

def send_verification_email(email, code):
    try:
        send_mail(
            subject='Подтверждение email',
            message=f'Ваш код подтверждения: {code}.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True, "Письмо отправлено"
    
    except Exception as e:
        return False, f"Ошибка отправки: {str(e)}"


def send_verification_sms(phone_number, code):
    try:
        send_sms(
            body=f'Ваш код подтверждения Профессия: {code}',
            originator=settings.DEFAULT_FROM_SMS,
            recipients=[phone_number],
            fail_silently=False,
        )
        return True, "СМС отправлено"

    except Exception as e:
        return False, f"Ошибка отправки СМС: {str(e)}"


def send_reset_password_email(email, recover_url):
    try:
        send_mail(
            subject='Сброс пароля',
            message=f'Перейдите по ссылке для сброса пароля: {recover_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True, "Письмо отправлено"
    
    except Exception as e:
        return False, f"Ошибка отправки: {str(e)}"


def send_reset_password_sms(phone_number, reset_code):

    try:
        send_sms(
            body=f'Код для сброса пароля Профессия: {reset_code}',
            originator=settings.DEFAULT_FROM_SMS,
            recipients=[phone_number],
            fail_silently=False,
        )
        return True, "СМС отправлено"
    
    except Exception as e:
        return False, f"Ошибка отправки СМС: {str(e)}"
    

def generate_registration_code(contact, password, contact_type='phone'):
    code = f"{secrets.randbelow(1000000):06d}"
    contact_cipher = encrypt_data(contact)
    cache_key = f'pending_registration_{contact_type}_{contact_cipher}'

    data = {
        'code': code,
        'contact': contact,
        'contact_type': contact_type,
        'password_hash': make_password(password),
        'created_at': django_timezone.now().isoformat(),
    }

    cache.set(cache_key, data, timeout=300)
    return code


def verify_registration_code(contact, user_code, contact_type):
    contact_cipher = encrypt_data(contact)
    cache_key = f'pending_registration_{contact_type}_{contact_cipher}'
    data = cache.get(cache_key)

    if not data:
        raise VerificationError('not_found', MSG_CODE_NOT_FOUND)
    
    attempts_key = f'reg_verify_attempts_{contact_type}_{contact_cipher}'
    attempts = cache.get(attempts_key, 0)

    if attempts >= MAX_VERIFY_ATTEMPTS:
        cache.delete(cache_key)
        cache.delete(attempts_key)
        raise VerificationError('too_many_attempts', MSG_TOO_MANY_ATTEMPTS)
    
    created_at = data.get('created_at')
    if created_at:
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elapsed = (django_timezone.now() -  created_at).total_seconds()
        if elapsed > 300:
            cache.delete(cache_key)
            cache.delete(attempts_key)
            raise VerificationError('expired', MSG_CODE_EXPIRED)
    
    if not hmac.compare_digest(data['code'], user_code):
        cache.set(attempts_key, attempts + 1, timeout=300)
        raise VerificationError('invalid', MSG_CODE_INVALID)

    cache.delete(cache_key)
    cache.delete(attempts_key)
    return {
        'contact': data['contact'],
        'contact_type': data['contact_type'],
        'password_hash': data['password_hash'],
    }


def check_contact_rate_limit(contact, contact_type='phone'):
    contact_hash = hashlib.sha256(contact.encode()).hexdigest()[:16]
    rate_key = f'rate_{contact_type}_{contact_hash}'

    if cache.get(rate_key):
        try:
            ttl = cache.ttl(rate_key)
            retry_after = ttl if ttl and ttl > 0 else 60
        except AttributeError:
            retry_after = 60

        return False, retry_after

    cache.set(rate_key, 1, timeout=60)
    return True, 0
