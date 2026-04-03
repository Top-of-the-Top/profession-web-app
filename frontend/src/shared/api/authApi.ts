// shared/api/authApi.ts
import { apiClient } from './interceptor';

export type RegisterBody =
  | { email: string; password: string }
  | { phone_number: string; password: string };

export type RegisterVerifyBody =
  | { email: string; code: string }
  | { phone_number: string; code: string };

export type ResetBody = { email: string } | { phone_number: string };

const publicAuth = { skipAuth: true as const };

export const authApi = {
  login(data: { email: string | null; phone_number: string | null; password: string; date_time: string }) {
    return apiClient.request('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  register(data: RegisterBody) {
    return apiClient.request('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  registerVerify(data: RegisterVerifyBody) {
    return apiClient.request('/api/auth/register/verify/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  resetRequest(data: ResetBody) {
    return apiClient.request('/api/auth/reset/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  recoverPhone(data: { phone_number: string; code: string }) {
    return apiClient.request('/api/auth/recover/phone/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  recoverEmail(data: { token: string; password_hash: string }) {
    return apiClient.request('/api/auth/recover/email/', {
      method: 'PATCH',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  recoverSet(data: { token: string; password_hash: string }) {
    return apiClient.request('/api/auth/recover/set/', {
      method: 'PATCH',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },
};
