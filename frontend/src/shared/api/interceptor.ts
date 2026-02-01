// shared/api/interceptor.ts
import { type ApiLandingResponse } from './types';
import { authEvents } from '../events/authEvents';

const API_URL = import.meta.env.VITE_API_URL;

type TokensResponse = {
  access_token: string;
  refresh_token: string;
};

class ApiClient {
  private buildHeaders(
    customHeaders?: HeadersInit,
    token?: string
  ): HeadersInit {
    return {
      'Content-Type': 'application/json',
      ...(customHeaders ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  private logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    authEvents.dispatchEvent(new Event('logout'));
  }

  private async refreshTokens(): Promise<TokensResponse | null> {
    const refresh_token = localStorage.getItem('refresh_token');
    if (!refresh_token) return null;

    const response = await fetch(`${API_URL}/api/token/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    });

    if (!response.ok) return null;

    const tokens: TokensResponse = await response.json();

    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);

    return tokens;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_URL}${endpoint}`;
		console.log(url)
    const accessToken = localStorage.getItem('access_token');

    let response = await fetch(url, {
      ...options,
      headers: this.buildHeaders(options.headers, accessToken ?? undefined),
    });

    if (response.status === 401) {
      const tokens = await this.refreshTokens();

      if (!tokens) {
        this.logout();
        throw new Error('AUTH_EXPIRED');
      }

      response = await fetch(url, {
        ...options,
        headers: this.buildHeaders(options.headers, tokens.access_token),
      });
    }

    if (!response.ok) {
      throw new Error(`API_ERROR_${response.status}`);
    }

    return response.json();
  }


  login(data: {
    email_cipher: string | null;
    phone_number_cipher: string | null;
    pass_hash: string;
    date_time: string;
  }) {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  register(data: {
    email_cipher: string | null;
    phone_number_cipher: string | null;
    pass_hash: string;
    date_time: string;
  }) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  resetRequest(data: {
    email_cipher: string | null;
    phone_number_cipher: string | null;
  }) {
    return this.request('/api/auth/reset', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  resetPassword(data: {
    password_hash: string;
    token: string;
  }) {
    return this.request('/api/auth/recover/set', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }


  getLandingCourses() {
    return this.request<ApiLandingResponse>('/api/landing/courses');
  }
}

export const apiClient = new ApiClient();
