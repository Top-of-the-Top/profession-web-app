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


export type PrepareDataOptions = {
  includePassword?: boolean;
  includeToken?: boolean;
  token?: string;
};

export const prepareAuthData = (
  emailOrPhone: string,
  password?: string,
  options: PrepareDataOptions = {}
) => {
  const validation = validateEmailOrPhone(emailOrPhone);
  
  if (!validation.isValid) {
    throw new Error('Invalid email or phone number');
  }

  const result: any = {
    email_cipher: validation.isEmail ? encryptData(validation.normalized) : null,
    phone_number_cipher: validation.isPhone ? encryptData(validation.normalized) : null,
    date_time: new Date().toISOString()
  };

  if (password && options.includePassword) {
    result.pass_hash = hashPassword(password);
  }

  if (options.includeToken && options.token) {
    result.token = options.token;
  }

  return result;
};

export const prepareResetPasswordData = (
  password: string,
  token: string
): {
  password_hash: string;
  token: string;
} => {
  return {
    password_hash: hashPassword(password),
    token: token
  };
};