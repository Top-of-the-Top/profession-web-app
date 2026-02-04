from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timezone, timedelta
import secrets
from django.utils import timezone as django_timezone
import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


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
  return {
    'access_token': str(refresh.access_token),
    'access_expires_at': datetime.fromtimestamp(access['exp'], tz=timezone.utc).isoformat(),
    'refresh_token': str(refresh),
    'refresh_expires_at': datetime.fromtimestamp(refresh['exp'], tz=timezone.utc).isoformat(),
  }


def decrypt_email(cipher_text: str) -> str:
  if not cipher_text:
    return ''
  
  try:
    encryption_key = os.getenv('ENCRYPTION_KEY', '')
    key_hex = (encryption_key or '').ljust(32, '0')[:32]
    
    try:
      key = bytes.fromhex(key_hex)
      if len(key) < 16:
        key = key.ljust(16, b'\x00')
      key = key[:16]
    except ValueError:
      key = hashlib.sha256(encryption_key.encode('utf-8')).digest()[:32]
    
    iv_hex = hashlib.sha256((encryption_key or 'default').encode('utf-8')).hexdigest()[:32]
    iv = bytes.fromhex(iv_hex)[:16]
    
    encrypted_data = base64.b64decode(cipher_text)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_data)
    decrypted = unpad(decrypted, AES.block_size)
    
    return decrypted.decode('utf-8')
    
  except Exception:
    return ''