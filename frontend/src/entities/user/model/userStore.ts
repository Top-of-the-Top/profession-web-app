import { create } from 'zustand';
import { profileApi, type ProfileData } from '../../../shared/api/profileApi';
import { authEvents } from '../../../shared/events/authEvents';
import { tokenService, type Tokens } from '../../../shared/lib/auth/tokenService';

export type User = ProfileData;

export interface UserStoreState {
  user: User | null;
  isLoading: boolean;
  isAuthChecked: boolean;
  setUser: (user: User | null) => void;
  fetchUser: () => Promise<void>;
  login: (tokens: Tokens) => Promise<void>;
  logout: () => void;
  clearUser: () => void;
}

export const useUserStore = create<UserStoreState>((set, get) => ({
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
    if (!tokenService.hasToken()) {
      set({ user: null, isLoading: false, isAuthChecked: true });
      return;
    }

    set({ isLoading: true });

    try {
      const user = await profileApi.getProfile();
      set({ user, isLoading: false, isAuthChecked: true });
    } catch (error) {
      const err = error as Error;

      if (
        err?.message === 'AUTH_EXPIRED' ||
        err?.message?.includes('API_ERROR_401')
      ) {
        tokenService.clearTokens();
      }

      set({ user: null, isLoading: false, isAuthChecked: true });
      throw error;
    }
  },

  login: async (tokens: Tokens) => {
    tokenService.setTokens(tokens);
    await get().fetchUser();
  },

  logout: () => {
    tokenService.clearTokens();
    set({ user: null, isLoading: false, isAuthChecked: true });
  },
}));

authEvents.addEventListener('logout', () => {
  useUserStore.getState().clearUser();
});
