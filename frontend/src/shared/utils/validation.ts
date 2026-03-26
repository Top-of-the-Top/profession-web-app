// shared/utils/validation.ts

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

export const prepareResetPasswordData = (
  password: string,
  token: string,
): { password_hash: string; token: string } => ({
  password_hash: password,
  token,
});