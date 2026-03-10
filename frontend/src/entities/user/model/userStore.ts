import { create } from 'zustand';
import { profileApi, type ProfileData } from '../../../shared/api/profileApi';
import { authEvents } from '../../../shared/events/authEvents';

export type User = ProfileData;

export interface UserStoreState {
  user: User | null;
  isLoading: boolean;
  isAuthChecked: boolean;
  setUser: (user: User | null) => void;
  fetchUser: () => Promise<void>;
  logout: () => void;
  clearUser: () => void;
}

export const useUserStore = create<UserStoreState>((set) => ({
  user: null,
  isLoading: false,
  isAuthChecked: false,

  setUser: (user) => set({ user }),

  clearUser: () =>
    set({
      user: null,
      isLoading: false,
      isAuthChecked: true,
    }),

  fetchUser: async () => {
    const accessToken = localStorage.getItem('access_token');

    // Если токена нет — просто помечаем, что проверка завершена
    if (!accessToken) {
      set({
        user: null,
        isLoading: false,
        isAuthChecked: true,
      });
      return;
    }

    set({ isLoading: true });

    try {
      const user = await profileApi.getProfile();

      set({
        user,
        isLoading: false,
        isAuthChecked: true,
      });
    } catch (error) {
      const err = error as Error;

      // 401 и истёкший токен — очищаем токены на всякий случай
      if (
        err?.message === 'AUTH_EXPIRED' ||
        err?.message?.includes('API_ERROR_401')
      ) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('access_expires_at');
        localStorage.removeItem('refresh_expires_at');
      }

      set({
        user: null,
        isLoading: false,
        isAuthChecked: true,
      });

      // Ошибку не игнорируем — пробрасываем выше
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('access_expires_at');
    localStorage.removeItem('refresh_expires_at');

    set({
      user: null,
      isLoading: false,
      isAuthChecked: true,
    });
  },
}));

// Глобальная реакция на logout из ApiClient (401 и т.п.)
authEvents.addEventListener('logout', () => {
  useUserStore.getState().clearUser();
});

