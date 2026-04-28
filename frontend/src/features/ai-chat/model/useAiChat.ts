import { useEffect } from 'react';
import { tokenService } from '@shared/lib/auth/tokenService';
import { useAiChatStore } from './aiChatStore';
import { aiChatWebSocketService } from './aiChatWebSocketService';

export function useAiChat(courseSlug: string | null | undefined) {
  const status = useAiChatStore((state) => state.status);
  const error = useAiChatStore((state) => state.error);
  const chats = useAiChatStore((state) => state.chats);
  const activeChatId = useAiChatStore((state) => state.activeChatId);
  const historyByChatId = useAiChatStore((state) => state.historyByChatId);
  const isAnswerStreaming = useAiChatStore((state) => state.isAnswerStreaming);
  const streamBuffer = useAiChatStore((state) => state.streamBuffer);
  const streamChatId = useAiChatStore((state) => state.streamChatId);
  const setActiveChatId = useAiChatStore((state) => state.setActiveChatId);

  useEffect(() => {
    if (!courseSlug || !tokenService.hasToken()) {
      aiChatWebSocketService.disconnect();
      return;
    }

    aiChatWebSocketService.connect(courseSlug);
    return () => {
      aiChatWebSocketService.disconnect();
    };
  }, [courseSlug]);

  return {
    status,
    error,
    chats,
    activeChatId,
    history: activeChatId ? historyByChatId[activeChatId] ?? [] : [],
    isAnswerStreaming,
    streamBuffer,
    streamChatId,
    setActiveChatId,
    startNewChat: () => aiChatWebSocketService.startNewChat(),
    deleteChat: (chatId: string) => aiChatWebSocketService.deleteChat(chatId),
    getHistory: (chatId: string) => aiChatWebSocketService.getHistory(chatId),
    sendMessage: (chatId: string, text: string) =>
      aiChatWebSocketService.sendMessage(chatId, text),
  };
}
