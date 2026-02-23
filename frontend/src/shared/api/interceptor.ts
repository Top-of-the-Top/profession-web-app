// shared/api/interceptor.ts
import { authEvents } from '../events/authEvents';

const API_URL = import.meta.env.VITE_API_URL;

export type TokensResponse = {
  access_token: string;
  refresh_token: string;
};

export class ApiClient {
  private buildHeaders(
    customHeaders?: HeadersInit,
    token?: string,
    isFormData?: boolean
  ): HeadersInit {
    // Создаем объект заголовков с правильной типизацией
    const headers: Record<string, string> = {};
    
    // Копируем кастомные заголовки, если они есть
    if (customHeaders) {
      if (customHeaders instanceof Headers) {
        // Если это объект Headers, конвертируем в Record
        customHeaders.forEach((value, key) => {
          headers[key] = value;
        });
      } else if (Array.isArray(customHeaders)) {
        // Если это массив массивов
        customHeaders.forEach(([key, value]) => {
          headers[key] = value;
        });
      } else {
        // Если это обычный объект
        Object.assign(headers, customHeaders);
      }
    }
    
    // Добавляем токен авторизации
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Добавляем Content-Type только если это НЕ FormData
    // и если заголовок еще не установлен
    if (!isFormData && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    
    return headers;
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

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_URL}${endpoint}`;
    const accessToken = localStorage.getItem('access_token');
    
    // Проверяем, является ли тело FormData
    const isFormData = options.body instanceof FormData;

    let response = await fetch(url, {
      ...options,
      headers: this.buildHeaders(options.headers, accessToken ?? undefined, isFormData),
    });

    if (!response.ok) {
      if (response.status === 401) {
        const tokens = await this.refreshTokens();
        if (!tokens) {
          this.logout();
          throw new Error('AUTH_EXPIRED');
        }
        response = await fetch(url, {
          ...options,
          headers: this.buildHeaders(options.headers, tokens.access_token, isFormData),
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