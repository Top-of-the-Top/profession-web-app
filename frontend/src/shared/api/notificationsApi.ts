import { apiClient } from './interceptor';

export type NotificationType = 'personal' | 'course' | 'system';

export interface NotificationDTO {
  id: number;
  title: string;
  message: string;
  notification_type: NotificationType;
  is_read: boolean;
  created_at: string;
  image_url: string | null;
}

export interface NotificationListResponse {
  results: NotificationDTO[];
  has_more: boolean;
}

export interface MarkAllReadResponse {
  marked: number;
}

export const notificationsApi = {
  getAll(beforeId?: number): Promise<NotificationListResponse> {
    const query = typeof beforeId === 'number' ? `?before_id=${beforeId}` : '';
    return apiClient.request<NotificationListResponse>(`/api/notifications/${query}`, {
      method: 'GET',
    });
  },

  markAllRead(): Promise<MarkAllReadResponse> {
    return apiClient.request<MarkAllReadResponse>('/api/notifications/read-all/', {
      method: 'POST',
    });
  },
};
