// shared/api/interceptor.ts
const API_URL = import.meta.env.VITE_API_URL;

class ApiClient {
  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_URL}${endpoint}`;

    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
      ...(token ? { Authorization: `Bearer: ${token}` } : {}),
    };

    let responce = await fetch(url, { ...options, headers });

    if (responce.status === 401) {
      const refresh_token = localStorage.getItem('refresh_token');
      if (refresh_token) {
        try {
          const refreshResponse = await fetch(`${API_URL}/api/token/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refresh_token }),
          });

          if (refreshResponse.ok) {
            const tokens = await refreshResponse.json();
            localStorage.setItem('access_token', tokens.access_token);
            localStorage.setItem('refresh_token', tokens.access_token);

            responce = await fetch(url, {
              ...options,
              headers: {
                ...headers,
                Authorization: `Bearer ${tokens.access_token}`,
              },
            });
          }
        } catch (error) {
          throw new Error(`API Error: ${responce.status}`);
        }
      }
    }
    return responce.json;
  }

  async login(data: {
    email_cipher: string | null;
    phone_number_cipher: string | null;
    pass_hash: string;
    date_time: string;
  }) {
    return this.request('api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async register(data: {
    email_cipher: string | null;
    phone_number_cipher: string | null;
    pass_hash: string;
    date_time: string;
  }) {
    return this.request('api/auht/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async resetRequest(data: {
    email_cipher: string | null;
    phone_number_cipher: string | null;
  }) {
    return this.request('api/auth/reset', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async resetPassword(data: { password_hash: string; token: string }) {
    return this.request('api/auth/recover/set', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async getLandingCourses() {
    return this.request('/api/landing/couses');
  }
}

export const apiClient = new ApiClient();
