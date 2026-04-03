import { authApi } from '../../../shared/api/authApi';
import { AuthTokensSchema } from '../../../schemas/auth/auth.schema';
import { RecoverPhoneTokenSchema } from '../../../schemas/auth/recoverPhone.schema';
import type { Tokens } from '../../../shared/lib/auth/tokenService';

export const verifyRecoverPhoneCode = async (data: {
  phone_number: string;
  code: string;
}) => {
  const raw = await authApi.recoverPhone(data);
  return RecoverPhoneTokenSchema.parse(raw);
};

function toTokens(parsed: ReturnType<typeof AuthTokensSchema.parse>): Tokens {
  return {
    access_token: parsed.access_token,
    refresh_token: parsed.refresh_token,
    access_expires_at: parsed.access_expires_at,
    refresh_expires_at: parsed.refresh_expires_at,
  };
}

export const recoverEmailPassword = async (data: {
  password_hash: string;
  token: string;
}): Promise<Tokens> => {
  const raw = await authApi.recoverEmail(data);
  const parsed = AuthTokensSchema.parse(raw);
  return toTokens(parsed);
};

export const recoverSetPassword = async (data: {
  password_hash: string;
  token: string;
}): Promise<Tokens> => {
  const raw = await authApi.recoverSet(data);
  const parsed = AuthTokensSchema.parse(raw);
  return toTokens(parsed);
};
