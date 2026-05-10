import { apiClient } from './interceptor';

export interface ApplicationUser {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export type ApplicationStatus = 'pending' | 'approved' | 'rejected';

export interface ApplicationItem {
  application_id: string;
  status: ApplicationStatus;
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
  reviewed_by: number | null;
  user: ApplicationUser;
}

export interface ApplicationReviewResponse {
  application_id: string;
  status: ApplicationStatus;
  reviewed_at: string;
  reviewed_by: number;
}

export const applicationApi = {
  apply(courseSlug: string): Promise<void> {
    return apiClient.request(`/api/v1/courses/${courseSlug}/applications/apply/`, {
      method: 'POST',
    });
  },

  withdraw(courseSlug: string): Promise<void> {
    return apiClient.request(`/api/v1/courses/${courseSlug}/applications/my/`, {
      method: 'DELETE',
    });
  },

  list(courseSlug: string, status?: ApplicationStatus): Promise<ApplicationItem[]> {
    const qs = status ? `?status=${status}` : '';
    return apiClient.request(`/api/v1/courses/${courseSlug}/applications/${qs}`, {
      method: 'GET',
    });
  },

  approve(courseSlug: string, applicationId: string): Promise<ApplicationReviewResponse> {
    return apiClient.request(
      `/api/v1/courses/${courseSlug}/applications/${applicationId}/approve/`,
      { method: 'POST' },
    );
  },

  reject(courseSlug: string, applicationId: string): Promise<ApplicationReviewResponse> {
    return apiClient.request(
      `/api/v1/courses/${courseSlug}/applications/${applicationId}/reject/`,
      { method: 'POST' },
    );
  },
};
