export const ROLES = {
  student: 'student',
  teacher: 'teacher',
  moderator: 'moderator',
} as const;

export type UserRole = (typeof ROLES)[keyof typeof ROLES];

export interface JwtPayload {
  user_id: number;
  role: UserRole;
  exp: number;
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const base64 = token.split('.')[1];
    if (!base64) return null;
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}

export function extractRoleFromToken(token: string | null): UserRole | null {
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload?.role) return null;
  const valid: readonly string[] = Object.values(ROLES);
  return valid.includes(payload.role) ? payload.role : null;
}

export function extractUserIdFromToken(token: string | null): number | null {
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  return payload?.user_id ?? null;
}
