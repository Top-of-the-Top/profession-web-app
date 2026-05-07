import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { BotMessageSquare, Menu, Plus, Send, Trash2, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button, Input } from '@shared/ui';
import { useAiChat } from '../model/useAiChat';
import styles from './AiChatPanel.module.css';

interface AiChatPanelProps {
  courseSlug: string;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) {
    return '';
  }
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatMarkdownForDisplay(value: string): string {
  return value.replace(/([^\n])(\s*)(#{1,6}\s+)/g, '$1\n\n$3');
}

function formatMarkdownForDisplay(value: string): string {
  return value.replace(/([^\n])(\s*)(#{1,6}\s+)/g, '$1\n\n$3');
}

export function AiChatPanel({ courseSlug }: AiChatPanelProps) {
  const {
    status,
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
  } = useAiChat(courseSlug);
  const [text, setText] = useState('');
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [deletingChatId, setDeletingChatId] = useState<string | null>(null);
  const [appearingChatIds, setAppearingChatIds] = useState<string[]>([]);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const preserveScrollRef = useRef<{
    pending: boolean;
    prevScrollHeight: number;
    prevScrollTop: number;
  }>({
    pending: false,
    prevScrollHeight: 0,
    prevScrollTop: 0,
  });
  const stickToBottomRef = useRef(true);
  const lastHistorySizeRef = useRef(0);
  const lastStreamSizeRef = useRef(0);
  const lastActiveChatIdRef = useRef<string | null>(null);
  const shouldScrollOnResponseRef = useRef(false);
  const autoCreateRequestedRef = useRef(false);
  const deleteDelayRef = useRef<number | null>(null);
  const appearFrameRef = useRef<number | null>(null);
  const prevChatIdsRef = useRef<string[]>([]);

  useEffect(() => {
    if (activeChatId) {
      getHistory(activeChatId);
    }
  }, [activeChatId, getHistory]);

  useEffect(() => {
    if (lastActiveChatIdRef.current !== activeChatId) {
      lastActiveChatIdRef.current = activeChatId;
      stickToBottomRef.current = true;
      lastHistorySizeRef.current = 0;
      lastStreamSizeRef.current = 0;
      shouldScrollOnResponseRef.current = false;
    }
  }, [activeChatId]);

  const activeStreamText = useMemo(() => {
    if (!isAnswerStreaming || !activeChatId || streamChatId !== activeChatId) {
      return '';
    }
    return streamBuffer;
  }, [activeChatId, isAnswerStreaming, streamBuffer, streamChatId]);

  const showStreamingBubble = Boolean(isAnswerStreaming && activeChatId && streamChatId === activeChatId);
  const showWaitingIndicator = showStreamingBubble && !activeStreamText;

  const onCreateChat = () => {
    startNewChat();
  };

  const onSendMessage = () => {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }
    stickToBottomRef.current = true;
    shouldScrollOnResponseRef.current = true;
    setText('');
    if (!activeChatId) {
      setPendingMessage(trimmed);
      if (!autoCreateRequestedRef.current) {
        autoCreateRequestedRef.current = true;
        startNewChat();
      }
      return;
    }
    sendMessage(activeChatId, trimmed);
  };

  const onLoadOlder = () => {
    if (!activeChatId || !hasOlder || isLoadingOlder || !messagesRef.current) {
      return;
    }
    const container = messagesRef.current;
    preserveScrollRef.current = {
      pending: true,
      prevScrollHeight: container.scrollHeight,
      prevScrollTop: container.scrollTop,
    };
    setIsLoadingOlder(true);
    loadOlderVisible(activeChatId);
  };

  const onMessagesScroll = () => {
    const container = messagesRef.current;
    if (!container) {
      return;
    }
    const distanceToBottom = container.scrollHeight - container.clientHeight - container.scrollTop;
    stickToBottomRef.current = distanceToBottom <= 24;
    if (container.scrollTop <= 40) {
      onLoadOlder();
    }
  };

  useEffect(() => {
    if (!isWidgetOpen) {
      autoCreateRequestedRef.current = false;
      return;
    }
    window.requestAnimationFrame(() => {
      if (!messagesRef.current) {
        return;
      }
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    });
  }, [isWidgetOpen]);

  useEffect(() => {
    if (!isWidgetOpen) {
      return;
    }
    if (chats.length > 0) {
      autoCreateRequestedRef.current = false;
      return;
    }
    if (autoCreateRequestedRef.current) {
      return;
    }
    autoCreateRequestedRef.current = true;
    startNewChat();
  }, [chats.length, isWidgetOpen, startNewChat]);

  useEffect(() => {
    const currentIds = chats.map((chat) => chat.chat_id);
    if (prevChatIdsRef.current.length === 0) {
      prevChatIdsRef.current = currentIds;
      return;
    }
    const previous = new Set(prevChatIdsRef.current);
    const added = currentIds.filter((id) => !previous.has(id));
    if (added.length > 0) {
      setAppearingChatIds((prev) => Array.from(new Set([...prev, ...added])));
      if (appearFrameRef.current) {
        window.cancelAnimationFrame(appearFrameRef.current);
      }
      appearFrameRef.current = window.requestAnimationFrame(() => {
        appearFrameRef.current = window.requestAnimationFrame(() => {
          setAppearingChatIds((prev) => prev.filter((id) => !added.includes(id)));
          appearFrameRef.current = null;
        });
      });
    }
    prevChatIdsRef.current = currentIds;
  }, [chats]);

  useEffect(() => {
    if (!activeChatId || !pendingMessage || status !== 'connected') {
      return;
    }
    sendMessage(activeChatId, pendingMessage);
    setPendingMessage(null);
  }, [activeChatId, pendingMessage, sendMessage, status]);

  useEffect(() => {
    if (!deletingChatId) {
      return;
    }
    const stillExists = chats.some((chat) => chat.chat_id === deletingChatId);
    if (!stillExists) {
      setDeletingChatId(null);
    }
  }, [chats, deletingChatId]);

  useEffect(() => {
    return () => {
      if (deleteDelayRef.current) {
        window.clearTimeout(deleteDelayRef.current);
      }
      if (appearFrameRef.current) {
        window.cancelAnimationFrame(appearFrameRef.current);
      }
    };
  }, []);

  useLayoutEffect(() => {
    const container = messagesRef.current;
    if (!container) {
      return;
    }
    if (preserveScrollRef.current.pending) {
      const { prevScrollHeight, prevScrollTop } = preserveScrollRef.current;
      container.scrollTop = container.scrollHeight - prevScrollHeight + prevScrollTop;
      preserveScrollRef.current.pending = false;
      setIsLoadingOlder(false);
      return;
    }

    if (shouldScrollOnResponseRef.current && showStreamingBubble) {
      container.scrollTop = container.scrollHeight;
      shouldScrollOnResponseRef.current = false;
    }

    const currentHistorySize = fullHistory.length;
    const currentStreamSize = activeStreamText.length;
    const hasNewHistoryItem = currentHistorySize > lastHistorySizeRef.current;
    const hasStreamUpdate = currentStreamSize !== lastStreamSizeRef.current;

    if (stickToBottomRef.current && (hasNewHistoryItem || hasStreamUpdate)) {
      container.scrollTop = container.scrollHeight;
    }

    lastHistorySizeRef.current = currentHistorySize;
    lastStreamSizeRef.current = currentStreamSize;
  }, [activeStreamText.length, fullHistory.length, showStreamingBubble, visibleHistory.length]);

  return (
    <section className={styles.floatingRoot}>
      <div className={`${styles.floatingWindow} ${isWidgetOpen ? styles.floatingWindowOpen : ''}`}>
        <div className={styles.panel}>
            <button
              type="button"
              className={`${styles.drawerBackdrop} ${isDrawerOpen ? styles.drawerBackdropVisible : ''}`}
              onClick={() => setIsDrawerOpen(false)}
              aria-label="Закрыть список чатов"
              aria-hidden={!isDrawerOpen}
              tabIndex={isDrawerOpen ? 0 : -1}
            />

            <aside className={`${styles.drawer} ${isDrawerOpen ? styles.drawerOpen : ''}`}>
              <div className={styles.drawerHeader}>
                <h4 className={styles.drawerTitle}>Чаты</h4>
                <Button
                  type="button"
                  size="icon-sm"
                  variant="ghost"
                  onClick={() => setIsDrawerOpen(false)}
                  aria-label="Закрыть список чатов"
                >
                  <X size={16} />
                </Button>
              </div>

              <div className={styles.drawerActions}>
                <Button type="button" size="icon-sm" onClick={onCreateChat}>
                  <Plus size={16} />
                </Button>
              </div>

              <div className={styles.chatList}>
                {!chats.length ? (
                  <p className={styles.chatListEmpty}>Пока нет чатов</p>
                ) : (
                  chats.map((chat) => (
                    <div
                      key={chat.chat_id}
                      className={`${styles.chatItem} ${activeChatId === chat.chat_id ? styles.chatItemActive : ''} ${deletingChatId === chat.chat_id ? styles.chatItemRemoving : ''} ${appearingChatIds.includes(chat.chat_id) ? styles.chatItemAppearing : ''}`}
                    >
                      <button
                        type="button"
                        className={styles.chatItemSelect}
                        onClick={() => {
                          setActiveChatId(chat.chat_id);
                          setIsDrawerOpen(false);
                        }}
                      >
                        <span className={styles.chatItemTitle}>{chat.title}</span>
                        <span className={styles.chatItemMeta}>{formatDateTime(chat.updated_at)}</span>
                      </button>
                      <Button
                        type="button"
                        size="icon-sm"
                        variant="outline"
                        onClick={() => {
                          if (chats.length <= 1 || deletingChatId) {
                            return;
                          }
                          setDeletingChatId(chat.chat_id);
                          if (deleteDelayRef.current) {
                            window.clearTimeout(deleteDelayRef.current);
                          }
                          deleteDelayRef.current = window.setTimeout(() => {
                            deleteChat(chat.chat_id);
                            deleteDelayRef.current = null;
                          }, 180);
                        }}
                        disabled={chats.length <= 1}
                        aria-label={`Удалить чат ${chat.title}`}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </aside>

            <header className={styles.header}>
              <div className={styles.titleRow}>
                <Button
                  type="button"
                  size="icon-sm"
                  variant="outline"
                  onClick={() => setIsDrawerOpen(true)}
                  aria-label="Открыть список чатов"
                >
                  <Menu size={16} />
                </Button>
                <h3 className={styles.title}>
                  <BotMessageSquare size={20} style={{ transform: 'translateY(1px)' }}/> <span>ИИ-помощник</span>
                </h3>
              </div>

              {/* <p className={styles.status}>{statusLabel(status)}</p>
              {error ? <p className={styles.error}>{error}</p> : null}

              <p className={styles.activeChatLabel}>
                {activeChatId
                  ? chats.find((chat) => chat.chat_id === activeChatId)?.title ?? 'Выбран чат'
                  : 'Выберите чат в списке слева'}
              </p> */}
            </header>

            <div ref={messagesRef} className={styles.messages} onScroll={onMessagesScroll}>
              {hasOlder ? (
                <p className={styles.historyHint}>
                  {isLoadingOlder ? 'Загружаем более ранние сообщения...' : 'Прокрутите выше для загрузки истории'}
                </p>
              ) : null}

              {/* {!fullHistory.length && !activeStreamText ? (
                <p className={styles.empty}>
                  Выберите чат или создайте новый, чтобы начать диалог
                </p>
              ) : null} */}

              {visibleHistory.map((message) => (
                <div
                  key={message.messageId}
                  className={`${styles.bubble} ${message.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant}`}
                >
                  <div className={styles.markdownContent}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {formatMarkdownForDisplay(message.content)}
                    </ReactMarkdown>
                  </div>
                  <span className={styles.meta}>{formatDateTime(message.createdAt)}</span>
                </div>
              ))}

              {showStreamingBubble ? (
                <div className={`${styles.bubble} ${styles.bubbleAssistant}`}>
                  <div className={styles.streamingContent}>
                    {showWaitingIndicator ? null : (
                      <div className={styles.markdownContent}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {formatMarkdownForDisplay(activeStreamText)}
                        </ReactMarkdown>
                      </div>
                    )}
                    <span className={styles.streamingDot} />
                  </div>
                </div>
              ) : null}
            </div>

            <div className={styles.composer}>
              <Input
                className={styles.input}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Введите сообщение..."
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    onSendMessage();
                  }
                }}
                disabled={status !== 'connected'}
              />
              <Button
                type="button"
                onClick={onSendMessage}
                disabled={status !== 'connected' || !text.trim()}
              >
                <Send />
              </Button>
            </div>
        </div>
      </div>

      <button
        type="button"
        className={styles.floatingToggle}
        onClick={() => {
          setIsWidgetOpen((prev) => {
            const next = !prev;
            if (!next) {
              setIsDrawerOpen(false);
            }
            return next;
          });
        }}
        aria-label={isWidgetOpen ? 'Свернуть ИИ-чат' : 'Открыть ИИ-чат'}
      >
        {isWidgetOpen ? <X size={20} /> : <BotMessageSquare size={20} />}
      </button>
    </section>
  );
}
