import { create } from 'zustand';
import { type NotificationState, type Notification } from '../types';

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  status: 'idle',
  error: null,

  setStatus: (status) => set({ status }),
  setError: (message) => set({ error: message }),

  setInitial: (notificationsArray: Notification[]) => {
    set((state) => {
      const seenIds = new Set<number>();
      const merged: Notification[] = [];

      for (const notification of state.notifications) {
        if (seenIds.has(notification.id)) continue;
        seenIds.add(notification.id);
        merged.push(notification);
      }

      for (const notification of notificationsArray) {
        if (seenIds.has(notification.id)) continue;
        seenIds.add(notification.id);
        merged.push(notification);
      }

      merged.sort(
        (a, b) => b.created_at.getTime() - a.created_at.getTime()
      );

      return {
        notifications: merged,
        unreadCount: state.unreadCount,
      };
    });
  },

  addNotification: (newNotification: Notification) => {
    set((state) => ({
      notifications: [newNotification, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    }));
  },

  removeNotification: (notificationId: number) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== notificationId),
    }));
  },

  markRead: () => set({ unreadCount: 0 }),

  clear: () => {
    set({ notifications: [], unreadCount: 0, error: null, status: 'idle' });
  },
}));
