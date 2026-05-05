import { useState, useRef, useEffect } from 'react';
import { useNotificationStore } from '../model/notification.store';
import styles from './NotificationBell.module.css';

const PAGE_SIZE = 10;

function formatDate(d: Date): string {
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const panelRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  const notifications = useNotificationStore((s) => s.notifications);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const markRead = useNotificationStore((s) => s.markRead);

  const visible = notifications.slice(0, visibleCount);
  const hasMore = visibleCount < notifications.length;

  function handleOpen() {
    setOpen((v) => {
      if (!v) {
        markRead();
        setVisibleCount(PAGE_SIZE);
      }
      return !v;
    });
  }

  // close on outside click
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        btnRef.current &&
        !btnRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  return (
    <div className={styles.wrapper}>
      <button
        ref={btnRef}
        className={styles.bell}
        aria-label="Уведомления"
        aria-expanded={open}
        onClick={handleOpen}
      >
        <img
          src={notifications.length > 0 ? '/bell-full.svg' : '/bell.svg'}
          alt=""
          width={22}
          height={22}
          decoding="async"
        />
        {unreadCount > 0 && (
          <span className={styles.badge}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div ref={panelRef} className={styles.panel} role="dialog" aria-label="Список уведомлений">
          <p className={styles.panelTitle}>Уведомления</p>

          {notifications.length === 0 && (
            <p className={styles.empty}>Уведомлений нет</p>
          )}

          {visible.length > 0 && (
            <ul className={styles.list}>
              {visible.map((n) => (
                <li key={n.id} className={styles.item}>
                  <span className={styles.itemTitle}>{n.title}</span>
                  <span className={styles.itemMessage}>{n.message}</span>
                  <span className={styles.itemDate}>{formatDate(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}

          {hasMore && (
            <button
              className={styles.loadMore}
              onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
            >
              Загрузить ещё
            </button>
          )}
        </div>
      )}
    </div>
  );
}
