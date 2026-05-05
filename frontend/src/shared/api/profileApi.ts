import { apiClient } from './interceptor';
import type { ApiUserResponse } from './types';

export type ProfileData = ApiUserResponse;

function normalizeGender(value: string | null): string | null {
  if (value == null) return null;
  if (value === 'Ж' || value === 'Женский') return 'Женский';
  if (value === 'М' || value === 'Мужской') return 'Мужской';
  return value;
}

function normalizeProfileData(raw: ApiUserResponse): ProfileData {
  return {
    ...raw,
    gender: normalizeGender(raw.gender),
    avatar: raw.avatar ?? raw.avatar_url ?? null,
  };
}

export interface UpdateProfilePayload {
  first_name?: string | null;
  last_name?: string | null;
  phone_number?: string | null;
  email?: string | null;
  gender?: string | null;
  birthday?: string | null;
  avatar_asset_id?: string | null;
}

export const profileApi = {
  getProfile(): Promise<ProfileData> {
    return apiClient
      .request<ApiUserResponse>('/api/profile/', { method: 'GET' })
      .then(normalizeProfileData);
  },

  updateProfile(payload: UpdateProfilePayload): Promise<{ status: 'success' }> {
    const body: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(payload)) {
      if (value === undefined) continue;
      body[key] = value;
    }
    return apiClient.request<{ status: 'success' }>('/api/profile/', {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },

  verifyEmailChange(code: string): Promise<{ status: 'success' }> {
    return apiClient.request<{ status: 'success' }>('/api/profile/verify-email/', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },

  verifyPhoneChange(code: string): Promise<{ status: 'success' }> {
    return apiClient.request<{ status: 'success' }>('/api/profile/verify-phone/', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },
};
