// shared/api/profileApi.ts
import { apiClient } from './interceptor';
import type { ApiUserResponse } from './types';

export type ProfileData = ApiUserResponse;

export interface UpdateProfilePayload {
  first_name?: string | null;
  last_name?: string | null;
  phone_number?: string | null;
  email?: string | null;
  gender?: string | null;
  birthday?: string | null;
  avatar?: File | null;
}

// shared/api/profileApi.ts

export const profileApi = {
  getProfile(): Promise<ProfileData> {
    return apiClient.request<ProfileData>('/api/app/profile/', { method: 'GET' });
  },

  updateProfile(payload: UpdateProfilePayload): Promise<{ status: 'success' }> {
    const formData = new FormData();

    Object.entries(payload).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (key === 'avatar' && value instanceof File) {
          formData.append(key, value);
        } else if (key === 'avatar' && value === null) {
          // Если нужно удалить аватар
          formData.append(key, '');
        } else {
          formData.append(key, String(value));
        }
      }
    });

    return apiClient.request<{ status: 'success' }>('/api/app/profile/', {
      method: 'PATCH',
      body: formData,
    });
  },

	// ПОКА НЕ ИСПОЛЬЗУЕТСЯ
  
  updateAvatar(file: File): Promise<{ status: 'success' }> {
    const formData = new FormData();
    formData.append('avatar', file);
    
    return apiClient.request<{ status: 'success' }>('/api/app/profile/', {
      method: 'PATCH',
      body: formData,
    });
  },
};