// shared/api/landingApi.ts
import { apiClient } from './interceptor';
import { type ApiLandingResponse } from './types';

export const landingApi = {
  /** Публичный каталог для лендинга: без Bearer, иначе протухший токен даёт 401. */
  getCourses() {
    return apiClient.request<ApiLandingResponse>('/api/landing/courses/', {
      method: 'GET',
      skipAuth: true,
    });
  },
};