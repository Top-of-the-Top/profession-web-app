/**
 * Ошибки fetch из apiClient: throw new Error(`API_ERROR_${status}: ${text}`)
 */
export type ParsedApiError = {
  status: number;
  body: unknown;
};

export function parseApiError(err: unknown): ParsedApiError | null {
  const msg = err instanceof Error ? err.message : String(err);
  const prefix = 'API_ERROR_';
  if (!msg.startsWith(prefix)) return null;
  const colon = msg.indexOf(':');
  if (colon === -1) return null;
  const status = Number(msg.slice(prefix.length, colon).trim());
  if (!Number.isFinite(status)) return null;
  const raw = msg.slice(colon + 1).trim();
  if (!raw) return { status, body: {} };
  try {
    return { status, body: JSON.parse(raw) };
  } catch {
    return { status, body: { detail: raw } };
  }
}

export function capitalizeFirst(text: string): string {
  const t = text.trim();
  if (!t) return t;
  return t.charAt(0).toLocaleUpperCase('ru-RU') + t.slice(1);
}
