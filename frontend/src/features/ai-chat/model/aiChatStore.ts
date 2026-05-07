import { create } from 'zustand';
import type {
  AiChatMessage,
  AiChatState,
  AiChatSummary,
} from './types';

const VISIBLE_BATCH_SIZE = 30;

function byUpdatedAtDesc(a: AiChatSummary, b: AiChatSummary) {
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

function createAssistantMessage(content: string): AiChatMessage {
  return {
    messageId: `assistant-${Date.now()}`,
    role: 'assistant',
    content,
    createdAt: new Date().toISOString(),
  };
}

export const useAiChatStore = create<AiChatState>((set, get) => ({
  status: 'idle',
  error: null,
  isLegacyProtocol: false,
  chats: [],
  activeChatId: null,
  historyByChatId: {},
  visibleStartByChatId: {},
  isAnswerStreaming: false,
  streamBuffer: '',
  streamChatId: null,

  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  setLegacyProtocol: (isLegacyProtocol) => set({ isLegacyProtocol }),

  setChats: (chats) => {
    const sorted = [...chats].sort(byUpdatedAtDesc);
    const state = get();
    const currentActiveExists = state.activeChatId
      ? sorted.some((chat) => chat.chat_id === state.activeChatId)
      : false;

    set({
      chats: sorted,
      activeChatId:
        currentActiveExists
          ? state.activeChatId
          : sorted[0]?.chat_id ?? null,
    });
  },

  addChat: (chat) =>
    set((state) => {
      const withoutCurrent = state.chats.filter(
        (item) => item.chat_id !== chat.chat_id
      );
      const nextChats = [chat, ...withoutCurrent].sort(byUpdatedAtDesc);
      return {
        chats: nextChats,
        activeChatId: chat.chat_id,
      };
    }),

  removeChat: (chatId) =>
    set((state) => {
      const chats = state.chats.filter((chat) => chat.chat_id !== chatId);
      const historyByChatId = { ...state.historyByChatId };
      const visibleStartByChatId = { ...state.visibleStartByChatId };
      delete historyByChatId[chatId];
      delete visibleStartByChatId[chatId];

      const shouldResetActive = state.activeChatId === chatId;
      const nextActive = shouldResetActive ? (chats[0]?.chat_id ?? null) : state.activeChatId;

      const shouldResetStream = state.streamChatId === chatId;

      return {
        chats,
        activeChatId: nextActive,
        historyByChatId,
        visibleStartByChatId,
        isAnswerStreaming: shouldResetStream ? false : state.isAnswerStreaming,
        streamBuffer: shouldResetStream ? '' : state.streamBuffer,
        streamChatId: shouldResetStream ? null : state.streamChatId,
      };
    }),

  setActiveChatId: (chatId) => set({ activeChatId: chatId }),

  setHistory: (chatId, history) =>
    set((state) => ({
      historyByChatId: {
        ...state.historyByChatId,
        [chatId]: history,
      },
      visibleStartByChatId: {
        ...state.visibleStartByChatId,
        [chatId]: Math.max(0, history.length - VISIBLE_BATCH_SIZE),
      },
    })),

  initVisibleWindow: (chatId, batchSize = VISIBLE_BATCH_SIZE) =>
    set((state) => {
      const history = state.historyByChatId[chatId] ?? [];
      return {
        visibleStartByChatId: {
          ...state.visibleStartByChatId,
          [chatId]: Math.max(0, history.length - batchSize),
        },
      };
    }),

  loadOlderVisible: (chatId, step = VISIBLE_BATCH_SIZE) =>
    set((state) => {
      const currentStart = state.visibleStartByChatId[chatId] ?? 0;
      const nextStart = Math.max(0, currentStart - step);
      if (nextStart === currentStart) {
        return state;
      }
      return {
        visibleStartByChatId: {
          ...state.visibleStartByChatId,
          [chatId]: nextStart,
        },
      };
    }),

  pinWindowToBottom: (chatId, batchSize = VISIBLE_BATCH_SIZE) =>
    set((state) => {
      const history = state.historyByChatId[chatId] ?? [];
      const nextStart = Math.max(0, history.length - batchSize);
      return {
        visibleStartByChatId: {
          ...state.visibleStartByChatId,
          [chatId]: nextStart,
        },
      };
    }),

  addMessage: (chatId, message) =>
    set((state) => {
      const existing = state.historyByChatId[chatId] ?? [];
      const nextHistory = [...existing, message];
      return {
        historyByChatId: {
          ...state.historyByChatId,
          [chatId]: nextHistory,
        },
        visibleStartByChatId: {
          ...state.visibleStartByChatId,
          [chatId]: Math.max(0, nextHistory.length - VISIBLE_BATCH_SIZE),
        },
      };
    }),

  startStreaming: (chatId) =>
    set({
      isAnswerStreaming: true,
      streamChatId: chatId,
      streamBuffer: '',
    }),

  appendStreamChunk: (chatId, chunk) =>
    set((state) => {
      if (!state.isAnswerStreaming || state.streamChatId !== chatId) {
        return {
          isAnswerStreaming: true,
          streamChatId: chatId,
          streamBuffer: chunk,
        };
      }

      return {
        streamBuffer: `${state.streamBuffer}${chunk}`,
      };
    }),

  finishStreaming: (chatId) =>
    set((state) => {
      if (!state.isAnswerStreaming || state.streamChatId !== chatId) {
        return state;
      }

      if (!state.streamBuffer.trim()) {
        return {
          isAnswerStreaming: false,
          streamBuffer: '',
          streamChatId: null,
        };
      }

      const existing = state.historyByChatId[chatId] ?? [];
      const assistantMessage = createAssistantMessage(state.streamBuffer);

      return {
        historyByChatId: {
          ...state.historyByChatId,
          [chatId]: [...existing, assistantMessage],
        },
        visibleStartByChatId: {
          ...state.visibleStartByChatId,
          [chatId]: Math.max(0, existing.length + 1 - VISIBLE_BATCH_SIZE),
        },
        isAnswerStreaming: false,
        streamBuffer: '',
        streamChatId: null,
      };
    }),

  clear: () =>
    set({
      status: 'idle',
      error: null,
      isLegacyProtocol: false,
      chats: [],
      activeChatId: null,
      historyByChatId: {},
      visibleStartByChatId: {},
      isAnswerStreaming: false,
      streamBuffer: '',
      streamChatId: null,
    }),
}));
