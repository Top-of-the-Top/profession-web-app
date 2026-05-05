import { authApi } from '@shared/api/authApi';
import { AuthTokensSchema, type AuthTokens } from '@schemas/auth/auth.schema';
import { RecoverPhoneTokenSchema } from '@schemas/auth/recoverPhone.schema';
import type { LoginPayload } from '@entities/user/model/userStore';
import type { UserRole } from '@shared/lib/rbac/roles';

export const verifyRecoverPhoneCode = async (data: {
  phone_number: string;
  code: string;
}) => {
  const raw = await authApi.recoverPhone(data);
  return RecoverPhoneTokenSchema.parse(raw);
};

function toLoginPayload(parsed: AuthTokens): LoginPayload {
  return {
    tokens: {
      access_token: parsed.access_token,
      refresh_token: parsed.refresh_token,
      access_expires_at: parsed.access_expires_at,
      refresh_expires_at: parsed.refresh_expires_at,
    },
    role: parsed.role as UserRole | undefined,
  };
}

export const recoverEmailPassword = async (data: {
  password: string;
  token: string;
}): Promise<LoginPayload> => {
  const raw = await authApi.recoverEmail({
    token: data.token,
    password: data.password,
  });
  const parsed = AuthTokensSchema.parse(raw);
  return toLoginPayload(parsed);
};

export const recoverSetPassword = async (data: {
  password: string;
  token: string;
}): Promise<LoginPayload> => {
  const raw = await authApi.recoverSet({
    token: data.token,
    password: data.password,
  });
  const parsed = AuthTokensSchema.parse(raw);
  return toLoginPayload(parsed);
};
