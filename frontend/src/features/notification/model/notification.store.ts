import { create } from 'zustand';
import { type NotificationState, type Notification } from '../types';

export const useNotificationStore = create<NotificationState>((set, _) => ({ // TODO: добавить GET
  notifications: new Array(),
  status: 'idle',
  error: null,

  setStatus: (status) => set({ status }),
  setError: (message) => set({ error: message }),

  setInitial: (notificationsArray: Notification[]) => {
		set({notifications: notificationsArray})
	},	

  addNotification: (newNotification: Notification) => {
    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));
  },

	removeNotification: (notificationId: Number) => {
		set((state) => ({
			notifications: [...state.notifications.filter((n) => { n.id !== notificationId})]
		}))
	},

  clear: () => {
    set({ notifications: new Array(), error: null, status: 'idle' });
  },
}));
