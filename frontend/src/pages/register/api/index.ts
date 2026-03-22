import { authApi } from '../../../shared/api/authApi';
import { prepareAuthData } from '../../../shared/utils/validation';
import type { Tokens } from '../../../context/AuthContext';
import { RegisterTokensSchema } from '../../../schemas/auth/register.schema';

interface RegisterParams {
  emailOrPhone: string;
  password: string;
}

/**
 * Регистрация. При ошибке валидации бэк отдаёт 403 и тело с полями (email, phone_number, password, …).
 */
export const registerUser = async ({
  emailOrPhone,
  password,
}: RegisterParams): Promise<Tokens> => {
  const payload = prepareAuthData(emailOrPhone, password, {
    includePassword: true,
  });
  const tokensRaw = await authApi.register(payload);
  return RegisterTokensSchema.parse(tokensRaw);
};
