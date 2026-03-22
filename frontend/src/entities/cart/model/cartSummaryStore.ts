import { create } from 'zustand';
import { cartApi } from '../../../shared/api/cartApi';
import { authEvents } from '../../../shared/events/authEvents';

type CartSummaryState = {
  hasItems: boolean | null;
  refresh: () => Promise<void>;
  reset: () => void;
  setHasItems: (hasItems: boolean) => void;
};

export const useCartSummaryStore = create<CartSummaryState>((set) => ({
  hasItems: null,

  reset: () => set({ hasItems: null }),

  setHasItems: (hasItems) => set({ hasItems }),

  refresh: async () => {
    if (!localStorage.getItem('access_token')) {
      set({ hasItems: false });
      return;
    }
    try {
      const data = await cartApi.getCart();
      set({ hasItems: (data.courses?.length ?? 0) > 0 });
    } catch (e) {
      const msg = e instanceof Error ? e.message : '';
      if (msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401')) {
        set({ hasItems: false });
        return;
      }
    }
  },
}));

authEvents.addEventListener('logout', () => {
  useCartSummaryStore.getState().reset();
});
