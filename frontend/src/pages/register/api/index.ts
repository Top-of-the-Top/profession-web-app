import { authApi } from '@shared/api/authApi';
import {
  buildRegisterPayload,
  buildRegisterVerifyPayload,
} from '@shared/utils/validation';
import {
  AuthTokensSchema,
  normalizeAuthTokensPayload,
  type AuthTokens,
} from '@schemas/auth/auth.schema';
import { RegisterCodeSentSchema } from '@schemas/auth/register.schema';
import type { LoginPayload } from '@entities/user/model/userStore';
import type { UserRole } from '@shared/lib/rbac/roles';

function isRecord(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function looksLikeTokenBundle(raw: unknown): boolean {
  const n = normalizeAuthTokensPayload(raw);
  return (
    isRecord(n) &&
    typeof n.access_token === 'string' &&
    n.access_token.length > 0 &&
    typeof n.refresh_token === 'string' &&
    n.refresh_token.length > 0
  );
}

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

export type RegisterStep1Result =
  | { flow: 'two_factor'; detail: string }
  | { flow: 'immediate'; loginPayload: LoginPayload };

export async function requestRegisterCode(params: {
  emailOrPhone: string;
  password: string;
}): Promise<RegisterStep1Result> {
  const payload = buildRegisterPayload(params.emailOrPhone, params.password);
  const raw = await authApi.register(payload);

  if (looksLikeTokenBundle(raw)) {
    const parsed = AuthTokensSchema.parse(raw);
    return {
      flow: 'immediate',
      loginPayload: toLoginPayload(parsed),
    };
  }

  const { detail } = RegisterCodeSentSchema.parse(raw);
  return { flow: 'two_factor', detail };
}

export async function completeRegisterWithCode(params: {
  kind: 'email' | 'phone';
  normalizedContact: string;
  code: string;
}): Promise<LoginPayload> {
  const body = buildRegisterVerifyPayload(
    params.kind,
    params.normalizedContact,
    params.code,
  );
  const raw = await authApi.registerVerify(body);
  const parsed = AuthTokensSchema.parse(raw);
  return toLoginPayload(parsed);
}
