import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { BotMessageSquare, Menu, Plus, Trash2, X } from 'lucide-react';
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

function statusLabel(status: string): string {
  switch (status) {
    case 'connecting':
      return 'Подключение...';
    case 'connected':
      return 'Подключено';
    case 'error':
      return 'Ошибка соединения';
    default:
      return 'Отключено';
  }
}

export function AiChatPanel({ courseSlug }: AiChatPanelProps) {
  const {
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
  } = useAiChat(courseSlug);
  const [text, setText] = useState('');
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const [animatedLength, setAnimatedLength] = useState(0);
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
  const streamTargetLengthRef = useRef(0);
  const tickCounterRef = useRef(0);

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
      streamTargetLengthRef.current = 0;
      tickCounterRef.current = 0;
      setAnimatedLength(0);
    }
  }, [activeChatId]);

  const activeStreamText = useMemo(() => {
    if (!isAnswerStreaming || !activeChatId || streamChatId !== activeChatId) {
      return '';
    }
    return streamBuffer;
  }, [activeChatId, isAnswerStreaming, streamBuffer, streamChatId]);

  const streamDisplayText = activeStreamText;

  useEffect(() => {
    if (!isAnswerStreaming) {
      streamTargetLengthRef.current = 0;
      tickCounterRef.current = 0;
      if (animatedLength !== 0) {
        console.log('[ai-chat:anim] stream stopped, reset animated length');
      }
      setAnimatedLength(0);
      return;
    }
    streamTargetLengthRef.current = streamDisplayText.length;
    if (streamDisplayText.length < animatedLength) {
      console.log(
        `[ai-chat:anim] clamp source=${streamDisplayText.length} animated=${animatedLength}`
      );
      setAnimatedLength(streamDisplayText.length);
    }
  }, [animatedLength, isAnswerStreaming, streamDisplayText]);

  useEffect(() => {
    if (!isAnswerStreaming) {
      return;
    }
    const timer = window.setInterval(() => {
      setAnimatedLength((prev) => {
        const target = streamTargetLengthRef.current;
        if (target <= prev) {
          return prev;
        }
        const remaining = target - prev;
        const step = remaining > 80 ? 3 : remaining > 30 ? 2 : 1;
        const next = Math.min(target, prev + step);
        tickCounterRef.current += 1;
        if (tickCounterRef.current % 20 === 0 || next === target) {
          console.log(
            `[ai-chat:anim] tick#${tickCounterRef.current} prev=${prev} next=${next} target=${target} step=${step} remaining=${remaining}`
          );
        }
        return next;
      });
    }, 14);

    return () => {
      window.clearInterval(timer);
    };
  }, [isAnswerStreaming]);

  const animatedStreamText = streamDisplayText.slice(0, animatedLength);
  const showStreamingBubble = Boolean(isAnswerStreaming && activeChatId && streamChatId === activeChatId);
  const showWaitingIndicator = showStreamingBubble && !streamDisplayText;

  const onCreateChat = () => {
    startNewChat();
  };

  const onDeleteChat = () => {
    if (!activeChatId) {
      return;
    }
    deleteChat(activeChatId);
  };

  const onSendMessage = () => {
    if (!activeChatId) {
      return;
    }
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }
    stickToBottomRef.current = true;
    shouldScrollOnResponseRef.current = true;
    streamTargetLengthRef.current = 0;
    tickCounterRef.current = 0;
    setAnimatedLength(0);
    console.log('[ai-chat:send] message sent, wait streaming bubble before scroll');
    sendMessage(activeChatId, trimmed);
    setText('');
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
      console.log('[ai-chat:scroll] moved to streaming bubble');
    }

    const currentHistorySize = fullHistory.length;
    const currentStreamSize = animatedLength;
    const hasNewHistoryItem = currentHistorySize > lastHistorySizeRef.current;
    const hasStreamUpdate = currentStreamSize !== lastStreamSizeRef.current;

    if (stickToBottomRef.current && (hasNewHistoryItem || hasStreamUpdate)) {
      container.scrollTop = container.scrollHeight;
    }

    lastHistorySizeRef.current = currentHistorySize;
    lastStreamSizeRef.current = currentStreamSize;
  }, [animatedLength, fullHistory.length, showStreamingBubble, visibleHistory.length]);

  return (
    <section className={styles.panel}>
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
                className={`${styles.chatItem} ${activeChatId === chat.chat_id ? styles.chatItemActive : ''}`}
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
                  variant="destructive"
                  onClick={() => deleteChat(chat.chat_id)}
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
            <BotMessageSquare size={16} /> <span>ИИ-помощник</span>
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
            <div>{message.content}</div>
            <span className={styles.meta}>{formatDateTime(message.createdAt)}</span>
          </div>
        ))}

        {showStreamingBubble ? (
          <div className={`${styles.bubble} ${styles.bubbleAssistant}`}>
            <div className={styles.streamingContent}>
              {showWaitingIndicator ? null : animatedStreamText}
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
          disabled={!activeChatId || status !== 'connected'}
        />
        <Button
          type="button"
          onClick={onSendMessage}
          disabled={!activeChatId || status !== 'connected' || !text.trim()}
        >
          Отправить
        </Button>
      </div>
    </section>
  );
}
