import { useEffect, useMemo, useState } from 'react';
import { BotMessageSquare, Plus, Trash2 } from 'lucide-react';
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
    history,
    isAnswerStreaming,
    streamBuffer,
    streamChatId,
    setActiveChatId,
    startNewChat,
    deleteChat,
    getHistory,
    sendMessage,
  } = useAiChat(courseSlug);
  const [text, setText] = useState('');

  useEffect(() => {
    if (activeChatId) {
      getHistory(activeChatId);
    }
  }, [activeChatId, getHistory]);

  const activeStreamText = useMemo(() => {
    if (!isAnswerStreaming || !activeChatId || streamChatId !== activeChatId) {
      return '';
    }
    return streamBuffer;
  }, [activeChatId, isAnswerStreaming, streamBuffer, streamChatId]);

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
    sendMessage(activeChatId, trimmed);
    setText('');
  };

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h3 className={styles.title}>
            <BotMessageSquare size={16} /> <span>ИИ-помощник</span>
          </h3>
        </div>

        <p className={styles.status}>{statusLabel(status)}</p>
        {error ? <p className={styles.error}>{error}</p> : null}

        <div className={styles.chatRow}>
          <select
            className={styles.chatSelect}
            value={activeChatId ?? ''}
            onChange={(event) => {
              const value = event.target.value;
              setActiveChatId(value || null);
            }}
          >
            <option value="" disabled>
              Выберите чат
            </option>
            {chats.map((chat) => (
              <option key={chat.chat_id} value={chat.chat_id}>
                {chat.title}
              </option>
            ))}
          </select>
          <Button type="button" size="icon-sm" onClick={onCreateChat}>
            <Plus size={16} />
          </Button>
          <Button
            type="button"
            size="icon-sm"
            variant="outline"
            onClick={onDeleteChat}
            disabled={!activeChatId}
          >
            <Trash2 size={16} />
          </Button>
        </div>
      </header>

      <div className={styles.messages}>
        {!history.length && !activeStreamText ? (
          <p className={styles.empty}>
            Выберите чат или создайте новый, чтобы начать диалог
          </p>
        ) : null}

        {history.map((message) => (
          <div
            key={message.messageId}
            className={`${styles.bubble} ${message.role === 'user' ? styles.bubbleUser : styles.bubbleAssistant}`}
          >
            <div>{message.content}</div>
            <span className={styles.meta}>{formatDateTime(message.createdAt)}</span>
          </div>
        ))}

        {activeStreamText ? (
          <div className={`${styles.bubble} ${styles.bubbleAssistant}`}>
            <div>{activeStreamText}</div>
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
