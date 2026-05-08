import base64
import hashlib
import logging
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

logger = logging.getLogger(__name__)


def _get_key_and_iv():
    encryption_key = os.getenv("ENCRYPTION_KEY", "")
    key_hex = (encryption_key or "").ljust(32, "0")[:32]

    try:
        key = bytes.fromhex(key_hex)
        if len(key) < 16:
            key = key.ljust(16, b"\x00")
        key = key[:16]
    except ValueError:
        key = hashlib.sha256(encryption_key.encode("utf-8")).digest()[:32]

    iv_hex = hashlib.sha256((encryption_key or "default").encode("utf-8")).hexdigest()[:32]
    iv = bytes.fromhex(iv_hex)[:16]

    return key, iv


def encrypt_data(plain_text: str) -> str:
    if not plain_text:
        return ""

    key, iv = _get_key_and_iv()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plain_text.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)

    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_data(cipher_text: str) -> str:
    if not cipher_text:
        return ""

    try:
        key, iv = _get_key_and_iv()
        encrypted = base64.b64decode(cipher_text)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)

        return decrypted.decode("utf-8")
    except (ValueError, TypeError, KeyError) as exc:
        logger.warning("Не удалось расшифровать данные: %s", exc)
        return ""
