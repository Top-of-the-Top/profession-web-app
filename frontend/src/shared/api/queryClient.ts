import { QueryClient } from '@tanstack/react-query';
import { authEvents } from '../events/authEvents';

function isAuthError(error: unknown): boolean {
  const msg = error instanceof Error ? error.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      retry: (failureCount, error) => {
        if (isAuthError(error)) return false;
        return failureCount < 1;
      },
    },
  },
});

authEvents.addEventListener('logout', () => {
  queryClient.clear();
});
