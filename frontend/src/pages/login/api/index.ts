// src/features/login/api/index.ts
import { authApi } from '../../../shared/api/authApi';
import { prepareAuthData } from '../../../shared/utils/validation';
import type { Tokens } from '../../../context/AuthContext';
import { AuthTokensSchema } from '../../../schemas/auth/auth.schema';

interface LoginParams {
  emailOrPhone: string;
  password: string;
}

/**
 * Выполняет логин через API и возвращает токены.
 * @throws Error с текстом ошибки, если неудачно
 */
export const loginUser = async ({
  emailOrPhone,
  password,
}: LoginParams): Promise<Tokens> => {
  try {
		
    const payload = prepareAuthData(emailOrPhone, password, { includePassword: true });
    const tokensRaw = await authApi.login(payload);
    // Проверка через Zod
    const tokens = AuthTokensSchema.parse(tokensRaw);
    return tokens;


  } catch (err: any) {
    if (err.message.includes('403')) {
      throw new Error('Неверная почта/телефон или пароль');
    }
    if (err.message.includes('500')) {
      throw new Error('Сервер временно недоступен. Попробуйте позже.');
    }
    throw err;
  }
};
