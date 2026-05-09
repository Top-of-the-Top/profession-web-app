import { useState, useRef, useEffect } from 'react';
import { useNotificationStore } from '../model/notification.store';
import { notificationsApi } from '@shared/api/notificationsApi';
import styles from './NotificationBell.module.css';

function formatDate(d: Date): string {
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function mapDTO(n: { id: number; title: string; message: string; notification_type: import('@shared/api/notificationsApi').NotificationType; is_read: boolean; created_at: string }) {
  return {
    id: n.id,
    title: n.title,
    message: n.message,
    notification_type: n.notification_type,
    is_read: n.is_read,
    created_at: new Date(n.created_at),
  };
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const panelRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  const notifications = useNotificationStore((s) => s.notifications);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const hasMore = useNotificationStore((s) => s.hasMore);
  const markRead = useNotificationStore((s) => s.markRead);
  const appendPage = useNotificationStore((s) => s.appendPage);

  function handleOpen() {
    setOpen((v) => !v);
  }

  function handleMarkAllRead() {
    if (unreadCount === 0) return;
    const prevState = useNotificationStore.getState();
    markRead();
    void notificationsApi.markAllRead().catch(() => {
      useNotificationStore.setState({
        notifications: prevState.notifications,
        unreadCount: prevState.unreadCount,
      });
    });
  }

  function handleLoadMore() {
    if (isLoadingMore || !hasMore || notifications.length === 0) return;
    const beforeId = notifications[notifications.length - 1]?.id;
    if (typeof beforeId !== 'number') return;
    setIsLoadingMore(true);
    void notificationsApi
      .getAll(beforeId)
      .then((response) => {
        appendPage(response.results.map(mapDTO), response.has_more);
      })
      .finally(() => setIsLoadingMore(false));
  }

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
          src={unreadCount > 0 ? '/bell-full.svg' : '/bell.svg'}
          alt=""
          width={25}
          height={25}
          decoding="async"
        />
        
      </button>

      {open && (
        <div ref={panelRef} className={styles.panel} role="dialog" aria-label="Список уведомлений">
          <div className={styles.panelHeader}>
            <p className={styles.panelTitle}>Уведомления</p>
            {unreadCount > 0 && (
              <button className={styles.markAllRead} onClick={handleMarkAllRead}>
                Отметить все прочитанными
              </button>
            )}
          </div>

          {notifications.length === 0 && (
            <p className={styles.empty}>Уведомлений нет</p>
          )}

          {notifications.length > 0 && (
            <ul className={styles.list}>
              {notifications.map((n) => (
                <li key={n.id} className={[styles.item, !n.is_read ? styles.itemUnread : ''].join(' ')}>
                  {!n.is_read && (
                    <span className={styles.itemUnreadDot} aria-hidden />
                  )}
                  <span className={styles.itemTitle}>{n.title}</span>
                  <span className={styles.itemMessage}>{n.message}</span>
                  <span className={styles.itemDate}>{formatDate(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}

          {hasMore && (
            <div className={styles.actionsRow}>
              <button
                className={styles.loadMore}
                onClick={handleLoadMore}
                disabled={isLoadingMore}
              >
                {isLoadingMore ? 'Загрузка...' : 'Загрузить ещё'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
