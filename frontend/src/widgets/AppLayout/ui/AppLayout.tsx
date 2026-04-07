import { Suspense, useEffect } from 'react';
import { Outlet, Link, NavLink, useLocation } from 'react-router-dom';
import {
  Sparkles,
  House,
  ShoppingBag,
  CalendarDays,
  ClipboardList,
} from 'lucide-react';
import {
  Button,
  Spinner,
} from '@shared/ui';
import { cn } from '@shared/lib/utils';
import { useUserStore } from '@entities/user/model/userStore';
import { tokenService } from '@shared/lib/auth/tokenService';
import { useCart } from '@shared/api/queries/cart';
import {
  connectNotificationSSE,
  disconnectNotificationSSE,
} from '../../../features/notification/model/notification.sse';

import styles from './AppLayout.module.css';

export default function AppLayout() {
  const { pathname } = useLocation();
  const user = useUserStore((state) => state.user);
  const hasToken = tokenService.hasToken();

  const { data: cart } = useCart();
  const cartHasItems = (cart?.courses?.length ?? 0) > 0;

  const initials = [user?.first_name?.at(0), user?.last_name?.at(-1)]
    .filter(Boolean)
    .join('');

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
    { href: '/app', label: 'Тосты', icon: Sparkles, id: 'toasts' },
    { href: '/app/home', label: 'Домашняя', icon: House, id: 'home' },
    {
      href: '/app/store',
      label: 'Магазин',
      icon: ShoppingBag,
      id: 'upload',
    },
    {
      href: '/app/modify',
      label: 'Расписание',
      icon: CalendarDays,
      id: 'modify',
    },
    {
      href: '/app/distribute',
      label: 'Задания',
      icon: ClipboardList,
      id: 'distribute',
    },
  ];

  return (
    <div className={styles.container}>
      <header className={styles.topbar}>
        <img src="/profession-logo-blue.svg" alt="Logo" className={styles.logo} />
        <div className={styles.topbarItem}>
          <Link className={styles.headerLink} to="cart" aria-label="Корзина">
            <img
              src={cartHasItems ? '/cart-full.svg' : '/cart.svg'}
              alt=""
              className={styles.cartHeaderIcon}
              width={20}
              height={20}
              decoding="async"
            />
          </Link>
          <Link to="profile" className={styles.headerLink}>
            <div className={styles.pfp}>
              {user?.avatar ? (
                <img src={user.avatar} alt="Profile" />
              ) : (
                <span className={styles.pfpFallback}>
                  {initials || 'U'}
                </span>
              )}
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
                const storeActive =
                  id === 'upload' &&
                  (pathname.startsWith('/app/store') ||
                    pathname.startsWith('/app/courses'));
                return (
                  <NavLink
                    key={href}
                    to={href}
                    end={href === '/app'}
                    className={({ isActive }) =>
                      cn(
                        styles.navLink,
                        styles[id],
                        (storeActive || isActive) && styles.navLinkActive,
                      )
                    }
                  >
                    <Button variant="secondary" className={styles.navButton}>
                      <Icon className={styles.navIcon} strokeWidth={2} />
                      <span>{label}</span>
                    </Button>
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* <div className={styles.statsSection}>
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
          </div> */}
        </div>

        <main className={styles.main}>
          <Suspense fallback={<Spinner full />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
