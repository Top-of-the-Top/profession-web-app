import { apiClient } from './interceptor';

export interface NotificationDTO {
  id: number;
  title: string;
  message: string;
  created_at: string;
  image_url?: string | null;
  [key: string]: unknown;
}

export const notificationsApi = {
  getAll(): Promise<NotificationDTO[]> {
    return apiClient.request<NotificationDTO[]>('/api/notifications/', { method: 'GET' });
  },
};
