// shared/utils/encryption.ts
import CryptoJS from 'crypto-js';

const ENCRYPTION_KEY = import.meta.env.VITE_ENCRYPTION_KEY;

// Детерминированное шифрование: один и тот же plaintext даёт один и тот же ciphertext,
// чтобы при логине по email/телефону бэкенд мог найти пользователя по совпадению cipher.
function getKeyAndIv(): { key: CryptoJS.lib.WordArray; iv: CryptoJS.lib.WordArray } {
  const keyHex = (ENCRYPTION_KEY || '').padEnd(32, '0').slice(0, 32);
  const key = CryptoJS.enc.Hex.parse(keyHex);
  const ivHex = CryptoJS.SHA256(ENCRYPTION_KEY || 'default').toString().slice(0, 32);
  const iv = CryptoJS.enc.Hex.parse(ivHex);
  return { key, iv };
}

export const encryptData = (value: string): string => {
  if (!value) throw new Error("Cannot encrypt empty value");
  const { key, iv } = getKeyAndIv();
  const encrypted = CryptoJS.AES.encrypt(value, key, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7,
  });
  return encrypted.toString();
};

export const decryptData = (cipherText: string): string => {
  if (!cipherText) return '';
  const { key, iv } = getKeyAndIv();
  const bytes = CryptoJS.AES.decrypt(cipherText, key, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7,
  });
  return bytes.toString(CryptoJS.enc.Utf8);
};