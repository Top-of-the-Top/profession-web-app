import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { authEvents } from '@shared/events/authEvents';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { notifyError } from '@shared/lib/sileo/notify';

function isAuthError(error: unknown): boolean {
  const msg = error instanceof Error ? error.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      if (isAuthError(error)) return;

      const parsed = parseApiError(error);
      const description = parsed
        ? `Статус ${parsed.status}`
        : 'Повторите попытку позже.';

      notifyError({ title: 'Ошибка загрузки данных', description });
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (isAuthError(error)) return;
      if (mutation.options.onError) return;

      const parsed = parseApiError(error);
      const description = parsed
        ? `Статус ${parsed.status}`
        : 'Повторите попытку позже.';

      notifyError({ title: 'Ошибка выполнения операции', description });
    },
  }),
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
