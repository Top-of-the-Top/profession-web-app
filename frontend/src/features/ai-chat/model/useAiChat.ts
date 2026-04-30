import { useCallback, useEffect } from 'react';
import { tokenService } from '@shared/lib/auth/tokenService';
import { useAiChatStore } from './aiChatStore';
import { aiChatWebSocketService } from './aiChatWebSocketService';

export function useAiChat(courseSlug: string | null | undefined) {
  const status = useAiChatStore((state) => state.status);
  const error = useAiChatStore((state) => state.error);
  const chats = useAiChatStore((state) => state.chats);
  const activeChatId = useAiChatStore((state) => state.activeChatId);
  const historyByChatId = useAiChatStore((state) => state.historyByChatId);
  const visibleStartByChatId = useAiChatStore((state) => state.visibleStartByChatId);
  const isAnswerStreaming = useAiChatStore((state) => state.isAnswerStreaming);
  const streamBuffer = useAiChatStore((state) => state.streamBuffer);
  const streamChatId = useAiChatStore((state) => state.streamChatId);
  const setActiveChatId = useAiChatStore((state) => state.setActiveChatId);
  const initVisibleWindow = useAiChatStore((state) => state.initVisibleWindow);
  const loadOlderVisibleInStore = useAiChatStore((state) => state.loadOlderVisible);
  const startNewChat = useCallback(() => aiChatWebSocketService.startNewChat(), []);
  const deleteChat = useCallback(
    (chatId: string) => aiChatWebSocketService.deleteChat(chatId),
    []
  );
  const getHistory = useCallback(
    (chatId: string) => aiChatWebSocketService.getHistory(chatId),
    []
  );
  const sendMessage = useCallback(
    (chatId: string, text: string) => aiChatWebSocketService.sendMessage(chatId, text),
    []
  );
  const loadOlderVisible = useCallback(
    (chatId: string) => loadOlderVisibleInStore(chatId),
    [loadOlderVisibleInStore]
  );

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

  useEffect(() => {
    if (!activeChatId) {
      return;
    }
    initVisibleWindow(activeChatId);
  }, [activeChatId, initVisibleWindow]);

  const fullHistory = activeChatId ? historyByChatId[activeChatId] ?? [] : [];
  const visibleStart = activeChatId ? visibleStartByChatId[activeChatId] ?? 0 : 0;
  const visibleHistory = fullHistory.slice(visibleStart);
  const hasOlder = visibleStart > 0;

  return {
    status,
    error,
    chats,
    activeChatId,
    fullHistory,
    visibleHistory,
    hasOlder,
    isAnswerStreaming,
    streamBuffer,
    streamChatId,
    setActiveChatId,
    startNewChat,
    deleteChat,
    getHistory,
    loadOlderVisible,
    sendMessage,
  };
}
