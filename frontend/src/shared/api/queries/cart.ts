import { useQuery } from '@tanstack/react-query';
import { cartApi } from '../cartApi';

export const cartKeys = {
  all: ['cart'] as const,
};

export function useCart(options?: { enabled?: boolean }) {
  const hasToken = Boolean(localStorage.getItem('access_token'));

  return useQuery({
    queryKey: cartKeys.all,
    queryFn: () => cartApi.getCart(),
    enabled: (options?.enabled ?? true) && hasToken,
  });
}
