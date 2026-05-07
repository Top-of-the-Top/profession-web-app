import { create } from 'zustand';
import { profileApi, type ProfileData } from '@shared/api/profileApi';
import { authEvents } from '@shared/events/authEvents';
import { tokenService, type Tokens } from '@shared/lib/auth/tokenService';
import {
  type UserRole,
  extractRoleFromToken,
  extractUserIdFromToken,
} from '@shared/lib/rbac/roles';

export type User = ProfileData;

export interface LoginPayload {
  tokens: Tokens;
  role?: UserRole;
}

export interface UserStoreState {
  user: User | null;
  role: UserRole | null;
  userId: number | null;
  isLoading: boolean;
  isAuthChecked: boolean;
  setUser: (user: User | null) => void;
  fetchUser: () => Promise<void>;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => void;
  clearUser: () => void;
}

function readRbacFromToken(): { role: UserRole | null; userId: number | null } {
  const token = tokenService.getAccessToken();
  return {
    role: extractRoleFromToken(token),
    userId: extractUserIdFromToken(token),
  };
}

export const useUserStore = create<UserStoreState>((set, get) => ({
  user: null,
  role: null,
  userId: null,
  isLoading: false,
  isAuthChecked: false,

  setUser: (user) => set({ user }),

  clearUser: () =>
    set({
      user: null,
      role: null,
      userId: null,
      isLoading: false,
      isAuthChecked: true,
    }),

  fetchUser: async () => {
    if (!tokenService.hasToken()) {
      set({ user: null, role: null, userId: null, isLoading: false, isAuthChecked: true });
      return;
    }

    set({ isLoading: true });

    try {
      const user = await profileApi.getProfile();
      const { role, userId } = readRbacFromToken();
      set({ user, role, userId, isLoading: false, isAuthChecked: true });
    } catch (error) {
      const err = error as Error;

      if (
        err?.message === 'AUTH_EXPIRED' ||
        err?.message?.includes('API_ERROR_401')
      ) {
        tokenService.clearTokens();
      }

      set({ user: null, role: null, userId: null, isLoading: false, isAuthChecked: true });
      throw error;
    }
  },

  login: async ({ tokens, role }: LoginPayload) => {
    tokenService.setTokens(tokens);

    if (role) {
      const userId = extractUserIdFromToken(tokens.access_token);
      set({ role, userId });
    }

    await get().fetchUser();
  },

  logout: () => {
    tokenService.clearTokens();
    set({ user: null, role: null, userId: null, isLoading: false, isAuthChecked: true });
  },
}));

authEvents.addEventListener('logout', () => {
  useUserStore.getState().clearUser();
});
