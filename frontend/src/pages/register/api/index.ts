// src/features/register/api/index.ts
import { authApi } from '../../../shared/api/authApi';
import { prepareAuthData } from '../../../shared/utils/validation';
import type { Tokens } from '../../../context/AuthContext';
import { RegisterTokensSchema } from '../../../schemas/auth/register.schema';

interface RegisterParams {
  emailOrPhone: string;
  password: string;
}

/**
 * Выполняет регистрацию через API и возвращает токены.
 * @throws Error с текстом ошибки, если неудачно
 */
export const registerUser = async ({
  emailOrPhone,
  password,
}: RegisterParams): Promise<Tokens> => {
  try {
		
    const payload = prepareAuthData(emailOrPhone, password, { includePassword: true });
		console.log(payload)
    const tokensRaw = await authApi.register(payload);
    // Проверка через Zod
    const tokens = RegisterTokensSchema.parse(tokensRaw);
    return tokens;


  } catch (err: any) {
		console.log(err)
    if (err.message.includes('403')) {
      throw new Error('Неверная почта/телефон или пароль');
    }
    if (err.message.includes('500')) {
      throw new Error('Сервер временно недоступен. Попробуйте позже.');
    }
    throw err;
  }
};
