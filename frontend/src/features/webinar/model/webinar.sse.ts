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
      type: 'webinar_started';
      webinar_id: string;
      course_slug: string;
      lesson_slug: string;
      started_at?: string;
    }
  | {
      type: 'webinar_start';
      webinar_id: string;
      course_slug?: string;
      lesson_slug?: string;
      started_at?: string;
    }
  | {
      type: 'webinar_ended';
      webinar_id: string;
      course_slug?: string;
      lesson_slug?: string;
    }
  | {
      type: 'webinar_end';
      webinar_id: string;
    }
  | {
      type: 'webinar_scheduled';
      webinar_id: string;
      course_slug?: string;
      lesson_slug?: string;
      scheduled_at: string | null;
    }
  | {
      type: 'webinar_schedule_changed';
      webinar_id: string;
      course_slug?: string;
      lesson_slug?: string;
      scheduled_at: string | null;
    }
  | {
      type: string;
      webinar_id: string;
      course_slug?: string;
      lesson_slug?: string;
      started_at?: string;
      scheduled_at?: string | null;
    };

interface ConnectWebinarSseParams {
  webinarId?: string | null;
  courseSlug?: string | null;
  lessonSlug?: string | null;
  onEvent: (event: WebinarSseEvent) => void;
  onError?: (message: string) => void;
}

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.trim() ?? '';
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY = 500;

const LOG_PREFIX = '[webinar SSE]';

function logSse(message: string, detail?: unknown) {
  if (detail !== undefined) {
    console.log(LOG_PREFIX, message, detail);
  } else {
    console.log(LOG_PREFIX, message);
  }
}

function buildSseUrl(webinarId?: string | null): string | null {
  const token = tokenService.getAccessToken();
  if (!token) {
    return null;
  }
  const params = new URLSearchParams();
  params.set('token', token);
  if (webinarId) {
    params.set('webinar_id', webinarId);
  }
  return `${API_URL}/api/v1/notifications/sse/?${params.toString()}`;
}

function parseWebinarEvent(raw: string): WebinarSseEvent | null {
  try {
    const payload = JSON.parse(raw) as Record<string, unknown>;
    if (
      payload &&
      typeof payload === 'object' &&
      typeof payload.type === 'string' &&
      typeof payload.webinar_id === 'string'
    ) {
      if (payload.type === 'recording_started' && typeof payload.recording_id === 'string') {
        return payload as WebinarSseEvent;
      }
      if (payload.type === 'recording_stopped' && typeof payload.recording_id === 'string') {
        return payload as WebinarSseEvent;
      }
      if (
        payload.type === 'webinar_started' &&
        typeof payload.course_slug === 'string' &&
        typeof payload.lesson_slug === 'string'
      ) {
        return payload as WebinarSseEvent;
      }
      if (payload.type === 'webinar_start') {
        return payload as WebinarSseEvent;
      }
      if (payload.type === 'webinar_ended') {
        return payload as WebinarSseEvent;
      }
      if (payload.type === 'webinar_end') {
        return payload as WebinarSseEvent;
      }
      if (payload.type === 'webinar_scheduled' && 'scheduled_at' in payload) {
        return payload as WebinarSseEvent;
      }
      if (payload.type === 'webinar_schedule_changed' && 'scheduled_at' in payload) {
        return payload as WebinarSseEvent;
      }
    }
    return null;
  } catch {
    return null;
  }
}

export function connectWebinarSSE({
  webinarId,
  courseSlug,
  lessonSlug,
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
    logSse('disconnect', { webinarId });
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
      logSse('connect skipped: no access token', { webinarId });
      onError?.('Нет access token для SSE');
      return;
    }

    logSse('connecting', {
      webinarId,
      connectionAttempt: reconnectAttempts + 1,
    });

    source = new EventSource(url);

    source.onopen = () => {
      reconnectAttempts = 0;
      logSse('open', { webinarId, readyState: source?.readyState });
    };

    source.onmessage = (event) => {
      const parsedEvent = parseWebinarEvent(event.data);
      if (!parsedEvent) {
        logSse('message ignored (parse or shape)', {
          webinarId,
          dataPreview:
            typeof event.data === 'string'
              ? event.data.slice(0, 200)
              : event.data,
        });
        return;
      }
      if (webinarId && parsedEvent.webinar_id !== webinarId) {
        logSse('message ignored (other webinar)', {
          expectedWebinarId: webinarId,
          payloadWebinarId: parsedEvent.webinar_id,
          type: parsedEvent.type,
        });
        return;
      }
      if (
        (!webinarId || parsedEvent.webinar_id !== webinarId) &&
        courseSlug &&
        lessonSlug &&
        (((('course_slug' in parsedEvent && parsedEvent.course_slug) || undefined) !== courseSlug) ||
          ((('lesson_slug' in parsedEvent && parsedEvent.lesson_slug) || undefined) !== lessonSlug))
      ) {
        const payloadCourseSlug =
          'course_slug' in parsedEvent ? parsedEvent.course_slug : undefined;
        const payloadLessonSlug =
          'lesson_slug' in parsedEvent ? parsedEvent.lesson_slug : undefined;
        logSse('message ignored (other lesson)', {
          expectedCourseSlug: courseSlug,
          expectedLessonSlug: lessonSlug,
          payloadCourseSlug,
          payloadLessonSlug,
          type: parsedEvent.type,
        });
        return;
      }
      logSse('event', parsedEvent);
      onEvent(parsedEvent);
    };

    source.onerror = () => {
      logSse('error / connection dropped', {
        webinarId,
        reconnectAttempts,
        willReconnect: !isClosed && reconnectAttempts < MAX_RECONNECT_ATTEMPTS,
      });
      if (source) {
        source.close();
        source = null;
      }

      if (isClosed) return;
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        logSse('give up after max reconnects', {
          webinarId,
          max: MAX_RECONNECT_ATTEMPTS,
        });
        onError?.('Ошибка соединения с сервером');
        return;
      }

      reconnectAttempts += 1;
      clearReconnectTimeout();
      reconnectTimeout = setTimeout(() => {
        logSse('reconnect scheduled', {
          webinarId,
          delayMs: BASE_RECONNECT_DELAY,
          retryNumber: reconnectAttempts,
        });
        connect();
      }, BASE_RECONNECT_DELAY);
    };
  };

  connect();

  return disconnect;
}
