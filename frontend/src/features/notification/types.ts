

import type { NotificationType } from '@shared/api/notificationsApi';

export type ConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'error'
  | 'disconnected'

export type Notification = {
  id: number;
  title: string;
  message: string;
  notification_type: NotificationType;
  is_read: boolean;
  created_at: Date;
}

export type NotificationState = {
  notifications: Array<Notification>;
  unreadCount: number;
  hasMore: boolean;

  status: ConnectionStatus;
  error: string | null;

  setStatus: (status: ConnectionStatus) => void;
  setError: (message: string | null) => void;

  setInitial: (notifications: Notification[], hasMore: boolean) => void;
  appendPage: (notifications: Notification[], hasMore: boolean) => void;
  addNotification: (notification: Notification) => void;
  removeNotification: (notificationId: number) => void;
  markRead: () => void;
  clear: () => void;
}