export interface Tokens {
  access_token: string;
  refresh_token: string;
  access_expires_at?: string;
  refresh_expires_at?: string;
}

const TOKEN_KEYS = [
  'access_token',
  'refresh_token',
  'access_expires_at',
  'refresh_expires_at',
] as const;

export const tokenService = {
  getAccessToken: (): string | null => localStorage.getItem('access_token'),

  getRefreshToken: (): string | null => localStorage.getItem('refresh_token'),

  hasToken: (): boolean => Boolean(localStorage.getItem('access_token')),

  setTokens(tokens: Tokens) {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    if (tokens.access_expires_at) {
      localStorage.setItem('access_expires_at', tokens.access_expires_at);
    }
    if (tokens.refresh_expires_at) {
      localStorage.setItem('refresh_expires_at', tokens.refresh_expires_at);
    }
  },

  clearTokens() {
    for (const key of TOKEN_KEYS) {
      localStorage.removeItem(key);
    }
  },
};
