export const AI_CHAT_CLIENT_MESSAGE_TYPES = {
  START_NEW_CHAT: 'start new chat',
  DELETE_CHAT: 'delete chat',
  GET_HISTORY: 'get history',
  SEND_MESSAGE: 'send message',
} as const;

export const AI_CHAT_SERVER_MESSAGE_TYPES = {
  CONNECTED: 'connected',
  CHAT_CREATED: 'chat created',
  CHAT_DELETED: 'chat deleted',
  HISTORY_RECEIVED: 'history received',
  STARTING_ANSWER: 'starting answer',
  STREAMING_RESPONSE: 'streaming response',
  FINISHING_ANSWER: 'finishing answer',
  ERROR: 'error',
} as const;

export type AiChatClientMessageType =
  (typeof AI_CHAT_CLIENT_MESSAGE_TYPES)[keyof typeof AI_CHAT_CLIENT_MESSAGE_TYPES];

export type AiChatServerMessageType =
  (typeof AI_CHAT_SERVER_MESSAGE_TYPES)[keyof typeof AI_CHAT_SERVER_MESSAGE_TYPES];

export type AiChatConnectionStatus = 'idle' | 'connecting' | 'connected' | 'error';

export interface AiChatSummary {
  chat_id: string;
  title: string;
  updated_at: string;
}

export interface AiHistoryMessageDto {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface AiChatMessage {
  messageId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

export type AiChatClientMessage =
  | {
      type: typeof AI_CHAT_CLIENT_MESSAGE_TYPES.START_NEW_CHAT;
      chat_id: '';
      content: Record<string, never>;
    }
  | {
      type: typeof AI_CHAT_CLIENT_MESSAGE_TYPES.DELETE_CHAT;
      chat_id: string;
      content: Record<string, never>;
    }
  | {
      type: typeof AI_CHAT_CLIENT_MESSAGE_TYPES.GET_HISTORY;
      chat_id: string;
      content: Record<string, never>;
    }
  | {
      type: typeof AI_CHAT_CLIENT_MESSAGE_TYPES.SEND_MESSAGE;
      chat_id: string;
      content: {
        text: string;
      };
    };

export type AiChatServerMessage =
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.CONNECTED;
      chat_id: string;
      content: {
        chats: AiChatSummary[];
      };
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.CHAT_CREATED;
      chat_id: string;
      content: { title?: string };
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.CHAT_DELETED;
      chat_id: string;
      content: Record<string, never>;
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.HISTORY_RECEIVED;
      chat_id: string;
      content: {
        history: AiHistoryMessageDto[];
      };
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.STARTING_ANSWER;
      chat_id: string;
      content: Record<string, never>;
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.STREAMING_RESPONSE;
      chat_id: string;
      content: {
        chunk: string;
      };
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.FINISHING_ANSWER;
      chat_id: string;
      content: Record<string, never>;
    }
  | {
      type: typeof AI_CHAT_SERVER_MESSAGE_TYPES.ERROR;
      chat_id: string;
      content: {
        message: string;
      };
    };

export interface AiChatState {
  status: AiChatConnectionStatus;
  error: string | null;
  isLegacyProtocol: boolean;
  chats: AiChatSummary[];
  activeChatId: string | null;
  historyByChatId: Record<string, AiChatMessage[]>;
  visibleStartByChatId: Record<string, number>;
  isAnswerStreaming: boolean;
  streamBuffer: string;
  streamChatId: string | null;
  setStatus: (status: AiChatConnectionStatus) => void;
  setError: (error: string | null) => void;
  setLegacyProtocol: (isLegacyProtocol: boolean) => void;
  setChats: (chats: AiChatSummary[]) => void;
  addChat: (chat: AiChatSummary) => void;
  removeChat: (chatId: string) => void;
  setActiveChatId: (chatId: string | null) => void;
  setHistory: (chatId: string, history: AiChatMessage[]) => void;
  initVisibleWindow: (chatId: string, batchSize?: number) => void;
  loadOlderVisible: (chatId: string, step?: number) => void;
  pinWindowToBottom: (chatId: string, batchSize?: number) => void;
  addMessage: (chatId: string, message: AiChatMessage) => void;
  startStreaming: (chatId: string) => void;
  appendStreamChunk: (chatId: string, chunk: string) => void;
  finishStreaming: (chatId: string) => void;
  clear: () => void;
}
