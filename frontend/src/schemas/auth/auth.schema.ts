import { z } from "zod";

function isRecord(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

/**
 * Достаёт плоский объект с токенами из обёрток (data/result/tokens) и camelCase.
 */
export function normalizeAuthTokensPayload(input: unknown): unknown {
  let cur: unknown = input;

  for (let depth = 0; depth < 4; depth += 1) {
    if (!isRecord(cur)) break;
    const nested =
      cur.data ?? cur.result ?? cur.tokens ?? cur.payload ?? cur.body;
    if (isRecord(nested) && ("access_token" in nested || "accessToken" in nested)) {
      cur = nested;
      continue;
    }
    break;
  }

  if (!isRecord(cur)) return input;

  const c = cur;
  if (!("access_token" in c) && !("accessToken" in c)) return input;

  return {
    access_token: c.access_token ?? c.accessToken,
    access_expires_at: c.access_expires_at ?? c.accessExpiresAt,
    refresh_token: c.refresh_token ?? c.refreshToken,
    refresh_expires_at: c.refresh_expires_at ?? c.refreshExpiresAt,
    role: c.role,
  };
}

function strField(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return String(v);
}

const AuthTokensInnerSchema = z
  .object({
    access_token: z.unknown().transform((v) => strField(v)),
    access_expires_at: z.unknown().optional().transform((v) => strField(v)),
    refresh_token: z.unknown().transform((v) => strField(v)),
    refresh_expires_at: z.unknown().optional().transform((v) => strField(v)),
    role: z.unknown().optional().transform((v) => {
      if (v === null || v === undefined) return undefined;
      return strField(v);
    }),
  })
  .passthrough()
  .transform((d) => {
    if (!d.access_token.trim() || !d.refresh_token.trim()) {
      throw new z.ZodError([
        {
          code: z.ZodIssueCode.custom,
          path: ["access_token"],
          message: "В ответе нет access_token или refresh_token",
        },
      ]);
    }
    return {
      access_token: d.access_token,
      access_expires_at: d.access_expires_at || undefined,
      refresh_token: d.refresh_token,
      refresh_expires_at: d.refresh_expires_at || undefined,
      role: d.role,
    };
  });

/** Ответ login / register/verify / recover с токенами (после нормализации). */
export const AuthTokensSchema = z.preprocess(
  normalizeAuthTokensPayload,
  AuthTokensInnerSchema,
);

export type AuthTokens = z.infer<typeof AuthTokensSchema>;
