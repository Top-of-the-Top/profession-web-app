// shared/api/landingApi.ts
import { apiClient } from './interceptor';
import { type ApiLandingResponse } from './types';

export const landingApi = {
  getCourses() {
    return apiClient.request<ApiLandingResponse>('/api/landing/courses/');
  },
};