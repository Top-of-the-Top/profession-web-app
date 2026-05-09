// shared/api/authApi.ts
import { apiClient } from './interceptor';

export interface AuthTokenBundleResponse {
  access_token: string;
  refresh_token: string;
  access_expires_at?: string;
  refresh_expires_at?: string;
  role?: string;
  [key: string]: unknown;
}

export type RegisterBody =
  | { email: string; password: string }
  | { phone_number: string; password: string };

export type RegisterVerifyBody =
  | { email: string; code: string }
  | { phone_number: string; code: string };

export type ResetBody = { email: string } | { phone_number: string };
export type YandexExchangeBody = { code: string; state: string };
export type VkExchangeBody = {
  code: string;
  state: string;
  code_verifier: string;
  device_id: string;
};

export interface RegisterCodeSentResponse {
  status: string;
  detail?: string;
  message?: string;
  [key: string]: unknown;
}

export interface ResetRequestResponse {
  status: string;
  detail?: string;
  [key: string]: unknown;
}

export interface RecoverPhoneResponse {
  token: string;
  [key: string]: unknown;
}

const publicAuth = { skipAuth: true as const };

export const authApi = {
  login(data: { email: string | null; phone_number: string | null; password: string; date_time: string }) {
    return apiClient.request<AuthTokenBundleResponse>('/api/v1/auth/login/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  register(data: RegisterBody) {
    return apiClient.request<AuthTokenBundleResponse | RegisterCodeSentResponse>('/api/v1/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  registerVerify(data: RegisterVerifyBody) {
    return apiClient.request<AuthTokenBundleResponse>('/api/v1/auth/register/verify/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  resetRequest(data: ResetBody) {
    return apiClient.request<ResetRequestResponse>('/api/v1/auth/reset/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  recoverPhone(data: { phone_number: string; code: string }) {
    return apiClient.request<RecoverPhoneResponse>('/api/v1/auth/recover/phone/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  recoverEmail(data: { token: string; password: string }) {
    return apiClient.request<AuthTokenBundleResponse>('/api/v1/auth/recover/set/', {
      method: 'PATCH',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  recoverSet(data: { token: string; password: string }) {
    return apiClient.request<AuthTokenBundleResponse>('/api/v1/auth/recover/set/', {
      method: 'PATCH',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  yandexExchange(data: YandexExchangeBody) {
    return apiClient.request<AuthTokenBundleResponse>('/api/v1/auth/yandex/exchange/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },

  vkExchange(data: VkExchangeBody) {
    return apiClient.request<AuthTokenBundleResponse>('/api/v1/auth/vk/exchange/', {
      method: 'POST',
      body: JSON.stringify(data),
      ...publicAuth,
    });
  },
};
