import { authEvents } from '@shared/events/authEvents';
import {
  setAuthLogoutReason,
  type AuthLogoutReason,
} from '@shared/lib/auth/logoutReason';
import { tokenService, type Tokens } from '@shared/lib/auth/tokenService';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? '';

export type TokensResponse = Tokens;

export type ApiRequestInit = RequestInit & { skipAuth?: boolean };

type RefreshTokensResult = {
  tokens: Tokens | null;
  reason?: AuthLogoutReason;
};

export class ApiClient {
  private refreshInflight: Promise<Tokens | null> | null = null;

  private static readonly ACCESS_REFRESH_WINDOW_MS = 30_000;

  private buildHeaders(
    customHeaders?: HeadersInit,
    token?: string,
    isFormData?: boolean
  ): HeadersInit {
    const headers: Record<string, string> = {};
    
    if (customHeaders) {
      if (customHeaders instanceof Headers) {
        customHeaders.forEach((value, key) => {
          headers[key] = value;
        });
      } else if (Array.isArray(customHeaders)) {
        customHeaders.forEach(([key, value]) => {
          headers[key] = value;
        });
      } else {
        Object.assign(headers, customHeaders);
      }
    }
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (!isFormData && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    
    return headers;
  }

  private logout(reason?: AuthLogoutReason) {
    if (reason) {
      setAuthLogoutReason(reason);
    }
    tokenService.clearTokens();
    authEvents.dispatchEvent(new Event('logout'));
  }

  private async refreshTokens(): Promise<Tokens | null> {
    if (this.refreshInflight) return this.refreshInflight;

    this.refreshInflight = this.performRefreshTokens()
      .then(({ tokens, reason }) => {
        if (!tokens && reason) {
          this.logout(reason);
        }
        return tokens;
      })
      .finally(() => {
      this.refreshInflight = null;
      });

    return this.refreshInflight;
  }

  private async performRefreshTokens(): Promise<RefreshTokensResult> {
    const refreshToken = tokenService.getRefreshToken();
    if (!refreshToken) {
      return { tokens: null, reason: 'refresh_token_missing' };
    }

    const refreshExpiresAt = tokenService.getRefreshExpiresAt();
    if (refreshExpiresAt) {
      const expiresAtMs = Date.parse(refreshExpiresAt);
      if (!Number.isFinite(expiresAtMs)) {
        return { tokens: null, reason: 'refresh_token_invalid' };
      }
      if (expiresAtMs <= Date.now()) {
        return { tokens: null, reason: 'refresh_token_expired' };
      }
    }

    let response: Response;
    try {
      response = await fetch(`${API_URL}/api/v1/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      return { tokens: null, reason: 'refresh_token_unavailable' };
    }

    if (!response.ok) {
      if (response.status === 400 || response.status === 401) {
        return { tokens: null, reason: 'refresh_token_invalid' };
      }
      return { tokens: null, reason: 'refresh_token_unavailable' };
    }

    const tokens: Tokens = await response.json();
    tokenService.setTokens(tokens);

    return { tokens };
  }

  private shouldRefreshAccessToken(): boolean {
    const accessExpiresAt = tokenService.getAccessExpiresAt();
    if (!accessExpiresAt) return false;

    const expiresAtMs = Date.parse(accessExpiresAt);
    if (!Number.isFinite(expiresAtMs)) return false;

    return expiresAtMs - Date.now() <= ApiClient.ACCESS_REFRESH_WINDOW_MS;
  }

  private async resolveAccessToken(skipAuth: boolean): Promise<string | undefined> {
    if (skipAuth) return undefined;

    if (this.shouldRefreshAccessToken()) {
      const tokens = await this.refreshTokens();
      if (tokens?.access_token) {
        return tokens.access_token;
      }
      const accessToken = tokenService.getAccessToken();
      if (!accessToken) {
        throw new Error('AUTH_EXPIRED');
      }
      return accessToken;
    }

    return tokenService.getAccessToken() ?? undefined;
  }

  async request<T>(endpoint: string, options: ApiRequestInit = {}): Promise<T> {
    const { skipAuth = false, ...fetchOptions } = options;
    const url = `${API_URL}${endpoint}`;
    const accessToken = await this.resolveAccessToken(skipAuth);

    const isFormData = fetchOptions.body instanceof FormData;

    let response = await fetch(url, {
      ...fetchOptions,
      headers: this.buildHeaders(fetchOptions.headers, accessToken, isFormData),
    });

    if (!response.ok) {
      if (response.status === 401 && !skipAuth) {
        const tokens = await this.refreshTokens();
        if (!tokens) {
          throw new Error('AUTH_EXPIRED');
        }
        response = await fetch(url, {
          ...fetchOptions,
          headers: this.buildHeaders(fetchOptions.headers, tokens.access_token, isFormData),
        });
      }
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`API_ERROR_${response.status}: ${text}`);
    }

    const text = await response.text();
    if (!text) return {} as T;
    return JSON.parse(text) as T;
  }
}

export const apiClient = new ApiClient();
