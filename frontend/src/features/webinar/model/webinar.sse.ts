import { tokenService } from '@shared/lib/auth/tokenService';

export type WebinarSseEvent =
  | {
      type: 'recording_started';
      webinar_id: string;
      recording_id: string;
      started_at: string;
    }
  | {
      type: 'recording_stopped';
      webinar_id: string;
      recording_id: string;
      ended_at: string;
    }
  | {
      type: 'webinar_ended';
      webinar_id: string;
    };

interface ConnectWebinarSseParams {
  webinarId: string;
  onEvent: (event: WebinarSseEvent) => void;
  onError?: (message: string) => void;
}

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? '';
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 500;

function buildSseUrl(webinarId: string): string | null {
  const token = tokenService.getAccessToken();
  if (!token) {
    return null;
  }

  return `${API_URL}/api/notifications/sse/?token=${encodeURIComponent(token)}&webinar_id=${encodeURIComponent(webinarId)}`;
}

function parseWebinarEvent(raw: string): WebinarSseEvent | null {
  try {
    const payload = JSON.parse(raw) as WebinarSseEvent;
    if (
      payload &&
      typeof payload === 'object' &&
      typeof payload.type === 'string' &&
      typeof payload.webinar_id === 'string'
    ) {
      if (payload.type === 'recording_started' && 'recording_id' in payload) {
        return payload;
      }
      if (payload.type === 'recording_stopped' && 'recording_id' in payload) {
        return payload;
      }
      if (payload.type === 'webinar_ended') {
        return payload;
      }
    }
    return null;
  } catch {
    return null;
  }
}

export function connectWebinarSSE({
  webinarId,
  onEvent,
  onError,
}: ConnectWebinarSseParams): () => void {
  let source: EventSource | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let reconnectAttempts = 0;
  let isClosed = false;

  const clearReconnectTimeout = () => {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  };

  const disconnect = () => {
    isClosed = true;
    clearReconnectTimeout();
    if (source) {
      source.close();
      source = null;
    }
  };

  const connect = () => {
    if (isClosed) return;
    const url = buildSseUrl(webinarId);
    if (!url) {
      onError?.('Нет access token для SSE');
      return;
    }

    source = new EventSource(url);

    source.onopen = () => {
      reconnectAttempts = 0;
    };

    source.onmessage = (event) => {
      const parsedEvent = parseWebinarEvent(event.data);
      if (!parsedEvent) return;
      if (parsedEvent.webinar_id !== webinarId) return;
      onEvent(parsedEvent);
    };

    source.onerror = () => {
      if (source) {
        source.close();
        source = null;
      }

      if (isClosed) return;
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        onError?.('Ошибка соединения с сервером');
        return;
      }

      reconnectAttempts += 1;
      clearReconnectTimeout();
      reconnectTimeout = setTimeout(() => {
        connect();
      }, BASE_RECONNECT_DELAY);
    };
  };

  connect();

  return disconnect;
}
