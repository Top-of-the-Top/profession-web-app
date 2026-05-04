export const validateEmailOrPhone = (value: string): {
  isValid: boolean;
  isEmail: boolean;
  isPhone: boolean;
  normalized: string;
} => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const trimmed = value.trim();
  const isEmail = emailRegex.test(trimmed);

  let isPhone = false;
  let normalizedPhone = '';

  if (!isEmail) {
    const digitsOnly = trimmed.replace(/\D/g, '');
    
    if (digitsOnly.length === 11 || digitsOnly.length === 10) {
      let normalizedDigits = digitsOnly;
      
      if (digitsOnly.length === 11 && digitsOnly.startsWith('8')) {
        normalizedDigits = '7' + digitsOnly.slice(1);
      }
      
      if (digitsOnly.length === 10) {
        normalizedDigits = '7' + digitsOnly;
      }
      
      if (normalizedDigits.startsWith('7')) {
        isPhone = true;
        normalizedPhone = `+${normalizedDigits}`;
      }
    }
  }

  return {
    isValid: isEmail || isPhone,
    isEmail,
    isPhone,
    normalized: isPhone ? normalizedPhone : trimmed
  };
};

type ContactValidation = ReturnType<typeof validateEmailOrPhone>;

function getValidatedContact(emailOrPhone: string): ContactValidation {
  const validation = validateEmailOrPhone(emailOrPhone);
  if (!validation.isValid) {
    throw new Error('Invalid email or phone number');
  }
  return validation;
}


export type PrepareDataOptions = {
  includePassword?: boolean;
  includeToken?: boolean;
  token?: string;
};

type AuthPayload = {
  email: string | null;
  phone_number: string | null;
  date_time: string;
  password?: string;
  token?: string;
};

export const prepareAuthData = (
  emailOrPhone: string,
  password?: string,
  options: PrepareDataOptions = {}
) => {
  const validation = getValidatedContact(emailOrPhone);

  const result: AuthPayload = {
    email: validation.isEmail ? validation.normalized : null,
    phone_number: validation.isPhone ? validation.normalized : null,
    date_time: new Date().toISOString()
  };

  if (password && options.includePassword) {
    result.password = password;
  }

  if (options.includeToken && options.token) {
    result.token = options.token;
  }

  return result;
};

/** Регистрация: одно поле контакта + пароль (без date_time). */
export type RegisterPayload =
  | { email: string; password: string }
  | { phone_number: string; password: string };

export function buildRegisterPayload(emailOrPhone: string, password: string): RegisterPayload {
  const validation = getValidatedContact(emailOrPhone);
  if (validation.isEmail) {
    return { email: validation.normalized, password };
  }
  return { phone_number: validation.normalized, password };
}

export type ResetPayload = { email: string } | { phone_number: string };

export function buildResetPayload(emailOrPhone: string): ResetPayload {
  const validation = getValidatedContact(emailOrPhone);
  if (validation.isEmail) {
    return { email: validation.normalized };
  }
  return { phone_number: validation.normalized };
}

export type RegisterVerifyPayload =
  | { email: string; code: string }
  | { phone_number: string; code: string };

export function buildRegisterVerifyPayload(
  kind: 'email' | 'phone',
  normalizedContact: string,
  code: string,
): RegisterVerifyPayload {
  if (kind === 'email') {
    return { email: normalizedContact, code };
  }
  return { phone_number: normalizedContact, code };
}

export const prepareResetPasswordData = (
  password: string,
  token: string,
): { password: string; token: string } => ({
  password,
  token,
});