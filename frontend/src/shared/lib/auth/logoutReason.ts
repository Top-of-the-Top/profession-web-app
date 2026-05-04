export type AuthLogoutReason =
  | 'refresh_token_expired'
  | 'refresh_token_invalid'
  | 'refresh_token_missing'
  | 'refresh_token_unavailable';

const AUTH_LOGOUT_REASON_KEY = 'auth_logout_reason';

export function setAuthLogoutReason(reason: AuthLogoutReason): void {
  sessionStorage.setItem(AUTH_LOGOUT_REASON_KEY, reason);
}

export function peekAuthLogoutReason(): AuthLogoutReason | null {
  const value = sessionStorage.getItem(AUTH_LOGOUT_REASON_KEY);
  if (
    value === 'refresh_token_expired' ||
    value === 'refresh_token_invalid' ||
    value === 'refresh_token_missing' ||
    value === 'refresh_token_unavailable'
  ) {
    return value;
  }
  return null;
}

export function consumeAuthLogoutReason(): AuthLogoutReason | null {
  const reason = peekAuthLogoutReason();
  if (reason) {
    sessionStorage.removeItem(AUTH_LOGOUT_REASON_KEY);
  }
  return reason;
}
