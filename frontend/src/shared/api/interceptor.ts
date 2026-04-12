import { authEvents } from '@shared/events/authEvents';
import { tokenService, type Tokens } from '@shared/lib/auth/tokenService';

const API_URL = import.meta.env.VITE_API_URL;

export type TokensResponse = Tokens;

/** Параметры fetch: без передачи Bearer (для логина, регистрации, сброса пароля и т.д.). */
export type ApiRequestInit = RequestInit & { skipAuth?: boolean };

export class ApiClient {
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

  private logout() {
    tokenService.clearTokens();
    authEvents.dispatchEvent(new Event('logout'));
  }

  private async refreshTokens(): Promise<Tokens | null> {
    const refreshToken = tokenService.getRefreshToken();
    if (!refreshToken) return null;

    const response = await fetch(`${API_URL}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return null;

    const tokens: Tokens = await response.json();
    tokenService.setTokens(tokens);

    return tokens;
  }

  async request<T>(endpoint: string, options: ApiRequestInit = {}): Promise<T> {
    const { skipAuth = false, ...fetchOptions } = options;
    const url = `${API_URL}${endpoint}`;
    const accessToken = skipAuth ? undefined : tokenService.getAccessToken() ?? undefined;

    const isFormData = fetchOptions.body instanceof FormData;

    let response = await fetch(url, {
      ...fetchOptions,
      headers: this.buildHeaders(fetchOptions.headers, accessToken, isFormData),
    });

    if (!response.ok) {
      if (response.status === 401 && !skipAuth) {
        const tokens = await this.refreshTokens();
        if (!tokens) {
          this.logout();
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
