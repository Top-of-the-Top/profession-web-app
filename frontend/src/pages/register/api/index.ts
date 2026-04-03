import { authApi } from '../../../shared/api/authApi';
import {
  buildRegisterPayload,
  buildRegisterVerifyPayload,
} from '../../../shared/utils/validation';
import type { Tokens } from '../../../shared/lib/auth/tokenService';
import {
  AuthTokensSchema,
  normalizeAuthTokensPayload,
} from '../../../schemas/auth/auth.schema';
import { RegisterCodeSentSchema } from '../../../schemas/auth/register.schema';

function isRecord(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

/** Ответ похож на токены (включая обёртку data / camelCase). */
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

export type RegisterStep1Result =
  | { flow: 'two_factor'; detail: string }
  | { flow: 'immediate'; tokens: Tokens };

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
      tokens: {
        access_token: parsed.access_token,
        refresh_token: parsed.refresh_token,
        access_expires_at: parsed.access_expires_at,
        refresh_expires_at: parsed.refresh_expires_at,
      },
    };
  }

  const { detail } = RegisterCodeSentSchema.parse(raw);
  return { flow: 'two_factor', detail };
}

export async function completeRegisterWithCode(params: {
  kind: 'email' | 'phone';
  normalizedContact: string;
  code: string;
}): Promise<Tokens> {
  const body = buildRegisterVerifyPayload(
    params.kind,
    params.normalizedContact,
    params.code,
  );
  const raw = await authApi.registerVerify(body);
  const parsed = AuthTokensSchema.parse(raw);
  return {
    access_token: parsed.access_token,
    refresh_token: parsed.refresh_token,
    access_expires_at: parsed.access_expires_at,
    refresh_expires_at: parsed.refresh_expires_at,
  };
}
