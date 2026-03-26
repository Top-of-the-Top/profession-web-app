import { authApi } from '../../../shared/api/authApi';
import { prepareAuthData } from '../../../shared/utils/validation';
import type { Tokens } from '../../../context/AuthContext';
import { AuthTokensSchema } from '../../../schemas/auth/auth.schema';

interface LoginParams {
  emailOrPhone: string;
  password: string;
}

/**
 * Логин. Ошибки сети / валидации DRF приходят как Error(`API_ERROR_${status}: …`).
 */
export const loginUser = async ({
  emailOrPhone,
  password,
}: LoginParams): Promise<Tokens> => {
  const payload = prepareAuthData(emailOrPhone, password, {
    includePassword: true,
  });
  const tokensRaw = await authApi.login(payload);
  return AuthTokensSchema.parse(tokensRaw);
};
