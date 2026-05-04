import { useQuery } from '@tanstack/react-query';
import { profileApi } from '../profileApi';

export const profileKeys = {
  all: ['profile'] as const,
  me: () => [...profileKeys.all, 'me'] as const,
};

export function useProfile(enabled = true) {
  return useQuery({
    queryKey: profileKeys.me(),
    queryFn: () => profileApi.getProfile(),
    enabled,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
