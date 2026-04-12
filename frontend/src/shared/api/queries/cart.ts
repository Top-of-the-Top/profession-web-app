import { useQuery } from '@tanstack/react-query';
import { cartApi } from '../cartApi';
import { tokenService } from '@shared/lib/auth/tokenService';

export const cartKeys = {
  all: ['cart'] as const,
};

export function useCart(options?: { enabled?: boolean }) {
  const hasToken = tokenService.hasToken();

  return useQuery({
    queryKey: cartKeys.all,
    queryFn: () => cartApi.getCart(),
    enabled: (options?.enabled ?? true) && hasToken,
  });
}
