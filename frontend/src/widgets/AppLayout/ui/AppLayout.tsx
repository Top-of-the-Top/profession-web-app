import { useEffect } from 'react';
import { Outlet, Link } from 'react-router-dom';
import {
  Upload,
  Edit,
  Users,
  ArrowRight,
  AlertCircle,
  ShoppingCart,
} from 'lucide-react';
import {
  Button,
  Alert,
  AlertDescription,
  AlertTitle,
} from '../../../shared/ui';
import { cn } from '../../../shared/lib/utils';
import { useUserStore } from '../../../entities/user/model/userStore';
import { useNotificationStore } from '../../../features/notification/model/notification.store';
import {
  connectNotificationSSE,
  disconnectNotificationSSE,
} from '../../../features/notification/model/notification.sse';

import styles from './AppLayout.module.css';

export default function AppLayout() {
  const user = useUserStore((state) => state.user);
  const status = useNotificationStore((state) => state.status);
  const error = useNotificationStore((state) => state.error);
  const hasToken = Boolean(localStorage.getItem('access_token'));

  useEffect(() => {
    if (hasToken && user) {
      console.info('[layout] SSE connect', { hasUser: true });
      connectNotificationSSE();
      return;
    }

    console.info('[layout] SSE disconnect', {
      hasToken,
      hasUser: Boolean(user),
    });
    disconnectNotificationSSE();
    return () => {
      disconnectNotificationSSE();
    };
  }, [hasToken, user]);

  const navItems = [
    { href: '/app/home', label: 'Домашняя', icon: ArrowRight, id: 'home' },
    {
      href: '/app/store',
      label: 'Магазин',
      icon: Upload,
      id: 'upload',
    },
    {
      href: '/app/modify',
      label: 'Расписание',
      icon: Edit,
      id: 'modify',
    },
    {
      href: '/app/distribute',
      label: 'Задания',
      icon: Users,
      id: 'distribute',
    },
  ];

  return (
    <div className={styles.container}>
      <header className={styles.topbar}>
        <img src="/profession-logo.svg" alt="Logo" className={styles.logo} />
        <div className={styles.topbarItem}>
          <Link className={styles.headerLink} to="cart">
            <ShoppingCart width="20px" height="20px" />
          </Link>
          <Link to="profile" className={styles.headerLink}>
            <div className={styles.pfp}>
              <img
                src={user?.avatar || '/ya.svg'}
                alt="Profile"
              />
            </div>
          </Link>
        </div>
      </header>
      <div className={styles.content}>
        <div className={styles.sidebar}>
          <div className={styles.navContainer}>
            <p>Меню</p>
            <nav className={styles.nav}>
              {navItems.map(({ href, label, icon: Icon, id }) => {
                return (
                  <Link
                    key={href}
                    to={href}
                    className={cn(styles.navLink, styles[id])}
                  >
                    <Button variant="secondary" className={styles.navButton}>
                      <Icon className={styles.navIcon} strokeWidth={2} />
                      <span>{label}</span>
                    </Button>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className={styles.statsSection}>
            {status === 'connecting' && (
              <div className={styles.loading}>Подключение к серверу...</div>
            )}

            {status === 'connected' && <></>}

            {status === 'disconnected' && (
              <>
                <Alert variant="destructive">
                  <AlertCircle />
                  <AlertTitle>Соединение потеряно</AlertTitle>
                  <AlertDescription>
                    Попытка восстановить соединение...
                  </AlertDescription>
                </Alert>
              </>
            )}

            {status === 'error' && (
              <>
                <Alert variant="destructive">
                  <AlertCircle />
                  <AlertTitle>Ошибка подключения</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
                <Button
                  onClick={() => {
                    if (hasToken && user) {
                      connectNotificationSSE();
                    }
                  }}
                >
                  Переподключиться
                </Button>
              </>
            )}
          </div>
        </div>

        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
