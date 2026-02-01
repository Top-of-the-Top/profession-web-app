// shared/utils/encryption.ts
import CryptoJS from 'crypto-js';

const ENCRYPTION_KEY = import.meta.env.VITE_ENCRYPTION_KEY;

export const encryptData = (data: string): string => {
  if (!data) return '';
  return CryptoJS.AES.encrypt(data, ENCRYPTION_KEY).toString();
};

export const decryptData = (cipherText: string): string => {
  if (!cipherText) return '';
  const bytes = CryptoJS.AES.decrypt(cipherText, ENCRYPTION_KEY);
  return bytes.toString(CryptoJS.enc.Utf8);
};