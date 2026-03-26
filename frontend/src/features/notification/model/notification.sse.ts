import { useNotificationStore } from './notification.store';
import { notifyInfo } from '../../../shared/lib/sileo/notify';

let source: EventSource | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

const API_URL = import.meta.env.VITE_API_URL;
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
    return;
  }

  store.setError('idle');
  store.setStatus('connecting');

  const token = localStorage.getItem('access_token');
  if (!token) {
    store.setStatus('error');
    store.setError('Нет access token для SSE');
    return;
  }

  const URL = `${API_URL}/api/notifications/sse/?token=${encodeURIComponent(token)}`;

  source = new EventSource(URL);

  source.onopen = () => {
    store.setStatus('connected');
    store.setError(null);
    reconnectAttempts = 0;
  };

  source.onmessage = (notification) => {
    try {
      const payload = JSON.parse(notification.data) as {
        id: number;
        title: string;
        message: string;
        created_at: string;
      };
      console.info('SSE notification received:', payload);

      store.addNotification({
        id: payload.id,
        title: payload.title,
        message: payload.message,
        created_at: new Date(payload.created_at),
      });
      notifyInfo({
        title: payload.title,
        description: payload.message,
      });
    } catch (err) {
      console.error(`SSE Error: ${err}`);
    }
  };

  source.onerror = () => {
    console.error('SSE error, reconnecting');

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
      console.info(`SSE reconnect`, {
        attempt: reconnectAttempts,
        max: MAX_RECONNECT_ATTEMPTS,
      });
      connectNotificationSSE();
    }, delay);
  };
}

export function disconnectNotificationSSE() {
  const store = useNotificationStore.getState();

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
