import { authApi } from '@shared/api/authApi';
import { prepareAuthData } from '@shared/utils/validation';
import { AuthTokensSchema } from '@schemas/auth/auth.schema';
import type { LoginPayload } from '@entities/user/model/userStore';
import type { UserRole } from '@shared/lib/rbac/roles';

interface LoginParams {
  emailOrPhone: string;
  password: string;
}

export const loginUser = async ({
  emailOrPhone,
  password,
}: LoginParams): Promise<LoginPayload> => {
  const payload = prepareAuthData(emailOrPhone, password, {
    includePassword: true,
  });
  const tokensRaw = await authApi.login(payload);
  const parsed = AuthTokensSchema.parse(tokensRaw);
  return {
    tokens: {
      access_token: parsed.access_token,
      refresh_token: parsed.refresh_token,
      access_expires_at: parsed.access_expires_at,
      refresh_expires_at: parsed.refresh_expires_at,
    },
    role: parsed.role as UserRole | undefined,
  };
};
