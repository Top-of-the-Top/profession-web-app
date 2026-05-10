import { useNotificationStore } from './notification.store';
import { notifyInfo } from '@shared/lib/sileo/notify';
import { tokenService } from '@shared/lib/auth/tokenService';

let source: EventSource | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? '';
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 500;

function clearReconnectTimeout() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
}

export function connectNotificationSSE() {
  const store = useNotificationStore.getState();

  if (source) {
    console.log('[notifications:sse] connect skipped, source already exists');
    return;
  }

  store.setError(null);
  store.setStatus('connecting');

  const token = tokenService.getAccessToken();
  console.log('[notifications:sse] connect start', {
    hasToken: Boolean(token),
    apiUrl: API_URL,
  });
  if (!token) {
    store.setStatus('error');
    store.setError('Нет access token для SSE');
    console.error('[notifications:sse] no access token, abort connect');
    return;
  }

  const URL = `${API_URL}/api/v1/notifications/sse/?token=${encodeURIComponent(token)}`;
  console.log('[notifications:sse] opening EventSource', { url: URL });

  source = new EventSource(URL);

  source.onopen = () => {
    console.log('[notifications:sse] connected');
    store.setStatus('connected');
    store.setError(null);
    reconnectAttempts = 0;
  };

  source.onmessage = (notification) => {
    console.log('[notifications:sse] raw message', notification.data);
    try {
      const payload = JSON.parse(notification.data) as {
        id: number;
        title: string;
        message: string;
        type?: string;
        notification_type?: 'personal' | 'course' | 'system';
        is_read?: boolean;
        created_at?: string;
      };

      const notificationType =
        payload.notification_type ??
        (payload.type === 'personal' || payload.type === 'course' || payload.type === 'system'
          ? payload.type
          : 'system');

      if (
        typeof payload.id !== 'number' ||
        typeof payload.title !== 'string' ||
        typeof payload.message !== 'string'
      ) {
        console.warn('[notifications:sse] message ignored, invalid shape', payload);
        return;
      }

      console.log('[notifications:sse] parsed message', payload);
      store.addNotification({
        id: payload.id,
        title: payload.title,
        message: payload.message,
        notification_type: notificationType,
        is_read: payload.is_read ?? false,
        created_at: new Date(payload.created_at ?? Date.now()),
      });
      console.log('[notifications:sse] added to store', {
        id: payload.id,
        notification_type: notificationType,
      });
      const toastDescription = payload.message.replace(/\n+/g, ' ').trim();
      notifyInfo({
        title: payload.title,
        description: toastDescription,
      });
    } catch (err) {
      console.error('[notifications:sse] message parse error', err, notification.data);
    }
  };

  source.onerror = (event) => {
    console.error('[notifications:sse] error, reconnecting', {
      readyState: source?.readyState,
      event,
    });

    if (source) {
      source.close();
      source = null;
    }

    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error(`SSE reconnect limit reached (${MAX_RECONNECT_ATTEMPTS})`);
      store.setStatus('error');
      store.setError('Ошибка соединения с сервером');
      reconnectAttempts = 0;
      return;
    }

    const delay = BASE_RECONNECT_DELAY;

    reconnectAttempts++;

    store.setStatus('connecting');
    store.setError(
      `Потеря соединения, переподключение (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`
    );

    clearReconnectTimeout();
    reconnectTimeout = setTimeout(() => {
      console.info(`[notifications:sse] reconnect`, {
        attempt: reconnectAttempts,
        max: MAX_RECONNECT_ATTEMPTS,
      });
      connectNotificationSSE();
    }, delay);
  };
}

export function disconnectNotificationSSE() {
  const store = useNotificationStore.getState();
  console.log('[notifications:sse] disconnect called');

  clearReconnectTimeout();
  reconnectAttempts = 0;

  if (source) {
    source.close();
    source = null;
  }

  store.setStatus('idle');
  store.setError(null);

  store.clear();
}
