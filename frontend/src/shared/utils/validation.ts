// shared/utils/validation.ts

import { encryptData } from "./encryption";
import { hashPassword } from "./hashing";


export const validateEmailOrPhone = (value: string): {
  isValid: boolean;
  isEmail: boolean;
  isPhone: boolean;
  normalized: string;
} => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const phoneInputRegex = /^(\+?\d[\d\s\-()]{7,20})$/;

  const trimmed = value.trim();
  const isEmail = emailRegex.test(trimmed);

  let isPhone = false;
  let normalizedPhone = '';

  if (!isEmail && phoneInputRegex.test(trimmed)) {
    let digits = trimmed.replace(/\D/g, '');

    // Нормализация РФ: 8XXXXXXXXXX → 7XXXXXXXXXX
    if (digits.startsWith('8') && digits.length === 11) {
      digits = '7' + digits.slice(1);
    }

    if (digits.length >= 10 && digits.length <= 15) {
      isPhone = true;
      normalizedPhone = `+${digits}`;
    }
  }

  return {
    isValid: isEmail || isPhone,
    isEmail,
    isPhone,
    normalized: isPhone ? normalizedPhone : trimmed
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