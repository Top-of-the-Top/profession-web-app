import { create } from 'zustand';
import { type NotificationState, type Notification } from '../types';

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  hasMore: false,
  status: 'idle',
  error: null,

  setStatus: (status) => set({ status }),
  setError: (message) => set({ error: message }),

  setInitial: (notificationsArray: Notification[], hasMore: boolean) => {
    const sorted = [...notificationsArray].sort(
      (a, b) => b.created_at.getTime() - a.created_at.getTime(),
    );
    const unreadCount = sorted.reduce((acc, n) => (n.is_read ? acc : acc + 1), 0);
    set({ notifications: sorted, unreadCount, hasMore });
  },

  appendPage: (notificationsArray: Notification[], hasMore: boolean) => {
    set((state) => {
      const existingIds = new Set(state.notifications.map((n) => n.id));
      const newOnes = notificationsArray.filter((n) => !existingIds.has(n.id));
      const merged = [...state.notifications, ...newOnes];
      merged.sort((a, b) => b.created_at.getTime() - a.created_at.getTime());
      const unreadCount = merged.reduce((acc, n) => (n.is_read ? acc : acc + 1), 0);
      return { notifications: merged, unreadCount, hasMore };
    });
  },

  addNotification: (newNotification: Notification) => {
    set((state) => {
      const filtered = state.notifications.filter((n) => n.id !== newNotification.id);
      const next = [newNotification, ...filtered];
      const unreadCount = next.reduce((acc, n) => (n.is_read ? acc : acc + 1), 0);
      return { notifications: next, unreadCount };
    });
  },

  removeNotification: (notificationId: number) => {
    set((state) => {
      const notifications = state.notifications.filter((n) => n.id !== notificationId);
      const unreadCount = notifications.reduce((acc, n) => (n.is_read ? acc : acc + 1), 0);
      return { notifications, unreadCount };
    });
  },

  markRead: () =>
    set((state) => ({
      unreadCount: 0,
      notifications: state.notifications.map((notification) => ({
        ...notification,
        is_read: true,
      })),
    })),

  clear: () => {
    set({ notifications: [], unreadCount: 0, hasMore: false, error: null, status: 'idle' });
  },
}));
