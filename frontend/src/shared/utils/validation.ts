// shared/utils/validation.ts

import { encryptData } from "./encryption";
import { hashPassword } from "./hashing";


// ОТДАЕТ: в .normalized: телефон всегда с плюсом, 8*** -> +7***, почта как есть
export const validateEmailOrPhone = (value: string): {
  isValid: boolean;
  isEmail: boolean;
  isPhone: boolean;
  normalized: string;
} => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const phoneRegex = /^\+?[1-9]\d{1,14}$/;

  const trimmed = value.trim();
  const isEmail = emailRegex.test(trimmed);

  let digits = trimmed.replace(/\D/g, '');

  // Нормализация для рф: 8XXXXXXXXXX → 7XXXXXXXXXX
  if (digits.startsWith('8') && digits.length === 11) {
    digits = '7' + digits.slice(1);
  }

  const isPhone = phoneRegex.test(digits);

  return {
    isValid: isEmail || isPhone,
    isEmail,
    isPhone,
    normalized: isPhone ? `+${digits}` : trimmed
  };
};


export const prepareAuthData = (
  emailOrPhone: string,
  password: string
): {
  email_cipher: string | null;
  phone_number_cipher: string | null;
  pass_hash: string;
  date_time: string;
} => {
  const validation = validateEmailOrPhone(emailOrPhone);
  
  if (!validation.isValid) {
    throw new Error('Invalid email or phone number');
  }

  const dateTime = new Date().toISOString();
  
  return {
    email_cipher: validation.isEmail ? encryptData(validation.normalized) : null,
    phone_number_cipher: validation.isPhone ? encryptData(validation.normalized) : null,
    pass_hash: hashPassword(password),
    date_time: dateTime
  };
};