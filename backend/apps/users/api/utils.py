import random
from django.core.cache import cache
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from datetime import datetime, timezone, timedelta
import secrets
from django.utils import timezone as django_timezone
import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad


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
    code = f"{random.randint(0, 999999):06d}"
    cache_key = f'verification_code_{user_id}_{contact_type}'

    data = {
        'code': code,
        'new_contact': new_contact,
        'attempts': 0,
        'created_at': django_timezone.now().isoformat()
    }

    cache.set(cache_key, data, timeout=60)

    return code

def get_verification_code_for_user(user_id, contact_type):
    cache_key = f'verification_code_{user_id}_{contact_type}'
    return cache.get(cache_key)

def delete_verification_code(user_id: int, contact_type: str):
    cache_key = f"verification_{user_id}_{contact_type}"
    cache.delete(cache_key)


def verify_code(user_id, contact_type, user_code):
    data = get_verification_code_for_user(user_id, contact_type)

    if not data:
        return False, None

    if data.get('attempts', 0) >= 5:
        delete_verification_code(user_id, contact_type)
        return False, None

    data['attempts'] = data.get('attempts', 0) + 1
    cache_key = f'verification_code_{user_id}_{contact_type}'
    cache.set(cache_key, data, timeout=cache.ttl(cache_key))

    if data['code'] == user_code:
        new_contact = data['new_contact']
        delete_verification_code(user_id, contact_type)
        return True, new_contact

    return False, None

def send_verification_email(email, code):
    try:
        send_mail(
            subject='Подтверждение смены email',
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

        print(f"[SMS] Отправка кода {code} на номер {phone_number}")
        return True, "СМС отправлено"
    except Exception as e:
        return False, f"Ошибка отправки СМС: {str(e)}"


def send_reset_password_email(email, recover_url):
    try:
        result = send_mail(
            subject='Сброс пароля',
            message=f'Перейдите по ссылке для сброса пароля: {recover_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        print(f'Письмо отправлено успешно. Результат: {result}')
        return True
    except Exception as e:
        print(f'Ошибка при отправке письма: {type(e).__name__}: {str(e)}')
        return False