import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../model/useWebinarChat';
import styles from './WebinarChat.module.css';
import { Send } from 'lucide-react';

interface WebinarChatProps {
  messages: ChatMessage[];
  uid: number;
  sendMessage: (text: string) => void;
}

export function WebinarChat({ messages, uid, sendMessage }: WebinarChatProps) {
  const [input, setInput] = useState('');
  const sentinelRef = useRef<HTMLDivElement>(null);
  const canSend = input.trim().length > 0;
  const formatTime = (value: number) =>
    new Date(value).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    });

  useEffect(() => {
    sentinelRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    sendMessage(trimmed);
    setInput('');
  };

  return (
    <div className={styles.panel}>
      <div className={styles.scrollArea}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={msg.senderId === String(uid) ? styles.msgOwn : styles.msgOther}
          >
            <div className={styles.msgMeta}>
              <span className={styles.senderName}>{msg.senderName}</span>
              <span className={styles.msgTime}>{formatTime(msg.createdAt)}</span>
            </div>
            <span className={styles.msgText}>{msg.text}</span>
          </div>
        ))}
        <div ref={sentinelRef} />
      </div>

      <div className={styles.inputRow}>
        <input
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSend();
          }}
          placeholder="Сообщение..."
        />
        <button
          type="button"
          className={styles.sendBtn}
          onClick={handleSend}
          disabled={!canSend}
        >
          <Send width={18} color='grey'/>
        </button>
      </div>
    </div>
  );
}
