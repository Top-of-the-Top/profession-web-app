// shared/utils/encryption.ts
import CryptoJS from 'crypto-js';

const ENCRYPTION_KEY = import.meta.env.VITE_ENCRYPTION_KEY;

export const encryptData = (value: string) => {
  if (!value) throw new Error("Cannot encrypt empty value");
  return CryptoJS.AES.encrypt(value, "secret-key").toString();
};

export const decryptData = (cipherText: string): string => {
  if (!cipherText) return '';
  const bytes = CryptoJS.AES.decrypt(cipherText, ENCRYPTION_KEY);
  return bytes.toString(CryptoJS.enc.Utf8);
};