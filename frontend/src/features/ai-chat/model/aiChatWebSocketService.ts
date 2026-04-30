import { authEvents } from '@shared/events/authEvents';
import { tokenService } from '@shared/lib/auth/tokenService';
import { useAiChatStore } from './aiChatStore';
import {
  AI_CHAT_CLIENT_MESSAGE_TYPES,
  AI_CHAT_SERVER_MESSAGE_TYPES,
  type AiChatClientMessage,
  type AiChatMessage,
  type AiChatServerMessage,
  type AiChatSummary,
} from './types';

const MAX_RECONNECT_ATTEMPTS = 8;
const BASE_RECONNECT_DELAY_MS = 500;
const MAX_RECONNECT_DELAY_MS = 8000;

function normalizeApiUrl(): URL {
  const envApiUrlRaw = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  const fallback = new URL(window.location.origin);

  if (!envApiUrlRaw) {
    return fallback;
  }

  const hasProtocol = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//.test(envApiUrlRaw);
  const candidate = hasProtocol ? envApiUrlRaw : `http://${envApiUrlRaw}`;

  try {
    return new URL(candidate);
  } catch {
    return fallback;
  }
}

function buildWebSocketUrl(courseSlug: string, token: string): string {
  const baseUrl = normalizeApiUrl();
  const protocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = new URL(baseUrl.origin);
  wsUrl.protocol = protocol;
  wsUrl.pathname = `/api/app/courses/${encodeURIComponent(courseSlug)}/ai/chat/`;
  wsUrl.searchParams.set('token', token);
  return wsUrl.toString();
}

function mapHistoryMessage(dto: {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}): AiChatMessage {
  return {
    messageId: dto.message_id,
    role: dto.role,
    content: dto.content,
    createdAt: dto.created_at,
  };
}

function deriveChatTitle(chats: AiChatSummary[], chatId: string): string {
  const maxIndex = chats.length + 1;
  return `Новый чат ${maxIndex}`;
}

class AiChatWebSocketService {
  private socket: WebSocket | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private activeCourseSlug: string | null = null;
  private shouldReconnect = false;
  private authListenerBound = false;
  private pendingDeleteChatId: string | null = null;

  connect(courseSlug: string) {
    const store = useAiChatStore.getState();
    if (!courseSlug.trim()) {
      return;
    }

    this.bindAuthListener();

    if (
      this.socket &&
      this.activeCourseSlug === courseSlug &&
      (this.socket.readyState === WebSocket.CONNECTING ||
        this.socket.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    this.clearReconnectTimeout();
    this.cleanupSocket();
    this.activeCourseSlug = courseSlug;
    this.shouldReconnect = true;

    const token = tokenService.getAccessToken();
    if (!token) {
      store.setStatus('error');
      store.setError('Нет access token для подключения AI-чата');
      return;
    }

    store.setStatus('connecting');
    store.setError(null);

    const wsUrl = buildWebSocketUrl(courseSlug, token);
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      const state = useAiChatStore.getState();
      state.setStatus('connected');
      state.setError(null);
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      this.handleServerMessage(event.data);
    };

    this.socket.onerror = () => {
      const state = useAiChatStore.getState();
      state.setStatus('error');
      state.setError('Ошибка websocket-соединения AI-чата');
    };

    this.socket.onclose = (event) => {
      this.cleanupSocket();
      this.handleClose(event.code);
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    this.reconnectAttempts = 0;
    this.clearReconnectTimeout();
    this.cleanupSocket();
    const store = useAiChatStore.getState();
    store.setStatus('idle');
    store.setError(null);
  }

  clearState() {
    useAiChatStore.getState().clear();
  }

  startNewChat() {
    this.send({
      type: AI_CHAT_CLIENT_MESSAGE_TYPES.START_NEW_CHAT,
      chat_id: '',
      content: {},
    });
  }

  deleteChat(chatId: string) {
    if (!chatId) {
      return;
    }
    this.pendingDeleteChatId = chatId;
    this.send({
      type: AI_CHAT_CLIENT_MESSAGE_TYPES.DELETE_CHAT,
      chat_id: chatId,
      content: {},
    });
  }

  getHistory(chatId: string) {
    if (!chatId) {
      return;
    }
    this.send({
      type: AI_CHAT_CLIENT_MESSAGE_TYPES.GET_HISTORY,
      chat_id: chatId,
      content: {},
    });
  }

  sendMessage(chatId: string, text: string) {
    const trimmed = text.trim();
    if (!chatId || !trimmed) {
      return;
    }

    useAiChatStore.getState().addMessage(chatId, {
      messageId: `local-user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      createdAt: new Date().toISOString(),
    });

    this.send({
      type: AI_CHAT_CLIENT_MESSAGE_TYPES.SEND_MESSAGE,
      chat_id: chatId,
      content: { text: trimmed },
    });
  }

  private send(message: AiChatClientMessage) {
    const store = useAiChatStore.getState();
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      store.setError('Соединение с AI-чатом не установлено');
      store.setStatus('error');
      return;
    }
    this.socket.send(JSON.stringify(message));
  }

  private handleServerMessage(rawData: string) {
    const store = useAiChatStore.getState();
    try {
      const message = JSON.parse(rawData) as AiChatServerMessage;
      switch (message.type) {
        case AI_CHAT_SERVER_MESSAGE_TYPES.CONNECTED: {
          store.setChats(message.content.chats ?? []);
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.CHAT_CREATED: {
          const title = deriveChatTitle(store.chats, message.chat_id);
          store.addChat({
            chat_id: message.chat_id,
            title,
            updated_at: new Date().toISOString(),
          });
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.CHAT_DELETED: {
          const deletedChatId = message.chat_id || this.pendingDeleteChatId;
          if (deletedChatId && store.chats.some((chat) => chat.chat_id === deletedChatId)) {
            store.removeChat(deletedChatId);
          }
          this.pendingDeleteChatId = null;
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.HISTORY_RECEIVED: {
          const history = (message.content.history ?? []).map(mapHistoryMessage);
          store.setHistory(message.chat_id, history);
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.STARTING_ANSWER: {
          store.startStreaming(message.chat_id);
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.STREAMING_RESPONSE: {
          store.appendStreamChunk(message.chat_id, message.content.chunk ?? '');
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.FINISHING_ANSWER: {
          store.finishStreaming(message.chat_id);
          break;
        }
        case AI_CHAT_SERVER_MESSAGE_TYPES.ERROR: {
          store.setError(message.content.message ?? 'Ошибка AI-чата');
          break;
        }
      }
    } catch {
      store.setError('Не удалось обработать ответ AI-чата');
    }
  }

  private handleClose(code: number) {
    const store = useAiChatStore.getState();

    if (code === 4003) {
      this.shouldReconnect = false;
      store.setStatus('error');
      store.setError('Сессия истекла. Выполните вход снова');
      tokenService.clearTokens();
      authEvents.dispatchEvent(new Event('logout'));
      return;
    }

    if (code === 4500) {
      store.setStatus('error');
      store.setError('Сервер AI-чата временно недоступен');
    }

    if (!this.shouldReconnect || !this.activeCourseSlug) {
      return;
    }

    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      store.setStatus('error');
      store.setError('Не удалось переподключиться к AI-чату');
      this.shouldReconnect = false;
      return;
    }

    this.reconnectAttempts += 1;
    const expDelay = Math.min(
      BASE_RECONNECT_DELAY_MS * 2 ** (this.reconnectAttempts - 1),
      MAX_RECONNECT_DELAY_MS
    );
    const jitter = Math.floor(Math.random() * 300);
    const delay = expDelay + jitter;

    store.setStatus('connecting');
    store.setError(
      `Переподключение к AI-чату (${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`
    );

    this.reconnectTimeout = setTimeout(() => {
      if (this.activeCourseSlug) {
        this.connect(this.activeCourseSlug);
      }
    }, delay);
  }

  private cleanupSocket() {
    if (!this.socket) {
      return;
    }
    this.socket.onopen = null;
    this.socket.onmessage = null;
    this.socket.onerror = null;
    this.socket.onclose = null;
    if (
      this.socket.readyState === WebSocket.OPEN ||
      this.socket.readyState === WebSocket.CONNECTING
    ) {
      this.socket.close();
    }
    this.socket = null;
  }

  private clearReconnectTimeout() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private bindAuthListener() {
    if (this.authListenerBound) {
      return;
    }
    authEvents.addEventListener('logout', () => {
      this.disconnect();
      this.clearState();
    });
    this.authListenerBound = true;
  }
}

export const aiChatWebSocketService = new AiChatWebSocketService();
