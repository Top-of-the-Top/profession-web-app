import { create } from 'zustand';
import type {
  AiChatMessage,
  AiChatState,
  AiChatSummary,
} from './types';

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
      const { [chatId]: _removed, ...historyByChatId } = state.historyByChatId;

      const shouldResetActive = state.activeChatId === chatId;
      const nextActive = shouldResetActive ? (chats[0]?.chat_id ?? null) : state.activeChatId;

      const shouldResetStream = state.streamChatId === chatId;

      return {
        chats,
        activeChatId: nextActive,
        historyByChatId,
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
    })),

  addMessage: (chatId, message) =>
    set((state) => {
      const existing = state.historyByChatId[chatId] ?? [];
      return {
        historyByChatId: {
          ...state.historyByChatId,
          [chatId]: [...existing, message],
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
      isAnswerStreaming: false,
      streamBuffer: '',
      streamChatId: null,
    }),
}));
