// shared/api/authApi.ts
import { apiClient } from './interceptor';

export const authApi = {
  login(data: { email: string | null; phone_number: string | null; password: string; date_time: string }) {
    return apiClient.request('/api/auth/login/', { method: 'POST', body: JSON.stringify(data) });
  },

  register(data: { email: string | null; phone_number: string | null; password: string; date_time: string }) {
    return apiClient.request('/api/auth/register/', { method: 'POST', body: JSON.stringify(data) });
  },

  resetRequest(data: { email: string | null; phone_number: string | null }) {
    return apiClient.request('/api/auth/reset/', { method: 'POST', body: JSON.stringify(data) });
  },

  resetPassword(data: { password_hash: string; token: string }) {
    return apiClient.request('/api/auth/recover/set/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};