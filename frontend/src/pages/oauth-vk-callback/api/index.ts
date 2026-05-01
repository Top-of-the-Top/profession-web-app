import { authApi } from '@shared/api/authApi';
import { AuthTokensSchema, type AuthTokens } from '@schemas/auth/auth.schema';
import type { LoginPayload } from '@entities/user/model/userStore';
import type { UserRole } from '@shared/lib/rbac/roles';

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

export async function exchangeVkCode(params: {
  code: string;
  state: string;
  codeVerifier: string;
  deviceId: string;
}): Promise<LoginPayload> {
  const raw = await authApi.vkExchange({
    code: params.code,
    state: params.state,
    code_verifier: params.codeVerifier,
    device_id: params.deviceId,
  });
  const parsed = AuthTokensSchema.parse(raw);
  return toLoginPayload(parsed);
}
