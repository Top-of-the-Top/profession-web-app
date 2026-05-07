import { Suspense, useEffect } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { Outlet, Link, NavLink, useLocation } from 'react-router-dom';
import { House, ShoppingBag, CalendarDays, ClipboardList } from 'lucide-react';
import { Button, Spinner, ContentErrorFallback } from '@shared/ui';
import { cn } from '@shared/lib/utils';
import { tokenService } from '@shared/lib/auth/tokenService';
import { useCart } from '@shared/api/queries/cart';
import { useProfile } from '@shared/api/queries/profile';
import { notificationsApi } from '@shared/api/notificationsApi';
import {
  connectNotificationSSE,
  disconnectNotificationSSE,
} from '../../../features/notification/model/notification.sse';
import { useNotificationStore } from '../../../features/notification/model/notification.store';
import { NotificationBell } from '../../../features/notification/ui/NotificationBell';
import { prefetchAppSidebarHref } from '@router/lazyPages';

import styles from './AppLayout.module.css';

function isFullBleedAppPage(pathname: string) {
  return pathname.endsWith('/webinar') || pathname.includes('/lesson/preview');
}

function isLessonEditorPage(pathname: string) {
  return pathname.includes('/courses/') && pathname.endsWith('/edit');
}

export default function AppLayout() {
  const { pathname } = useLocation();
  const lessonEditorLayout = isLessonEditorPage(pathname);
  const hasToken = tokenService.hasToken();
  const { data: user } = useProfile(hasToken);

  const { data: cart } = useCart();
  const cartHasItems = (cart?.courses?.length ?? 0) > 0;

  const initials = [user?.first_name?.at(0), user?.last_name?.at(-1)]
    .filter(Boolean)
    .join('');

  const setInitial = useNotificationStore((s) => s.setInitial);

  useEffect(() => {
    if (hasToken && user) {
      void notificationsApi
        .getAll()
        .then((notifications) => {
          setInitial(
            notifications.map((n) => ({
              id: n.id,
              title: n.title,
              message: n.message,
              created_at: new Date(n.created_at),
            }))
          );
        })
        .catch(() => {
          setInitial([]);
        })
        .finally(() => {
          connectNotificationSSE();
        });
      return;
    }

    disconnectNotificationSSE();
    return () => {
      disconnectNotificationSSE();
    };
  }, [hasToken, user]);

  const navItems = [
    { href: '/app', label: 'Домашняя', icon: House, id: 'home' },
    {
      href: '/app/store',
      label: 'Магазин',
      icon: ShoppingBag,
      id: 'upload',
    },
    {
      href: '/app/schedule',
      label: 'Расписание',
      icon: CalendarDays,
      id: 'schedule',
    },
    {
      href: '/app/homeworks',
      label: 'Задания',
      icon: ClipboardList,
      id: 'distribute',
    },
  ];

  return (
    <div className={styles.container}>
      <header className={styles.topbar}>
        <img
          src="/profession-logo-blue.svg"
          alt="Logo"
          className={styles.logo}
        />
        <div className={styles.topbarItem}>
          <NotificationBell />
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
                <span className={styles.pfpFallback}>{initials || 'U'}</span>
              )}
            </div>
          </Link>
        </div>
      </header>
      <div className={styles.content}>
        <div className={styles.sidebar}>
          <div className={styles.navContainer}>
            <nav className={styles.nav}>
              {navItems.map(({ href, label, icon: Icon, id }) => {
                return (
                  <NavLink
                    key={href}
                    to={href}
                    end={href === '/app'}
                    onPointerEnter={() => {
                      prefetchAppSidebarHref(href);
                    }}
                    onFocus={() => {
                      prefetchAppSidebarHref(href);
                    }}
                    className={({ isActive }) =>
                      cn(
                        styles.navLink,
                        styles[id],
                        isActive && styles.navLinkActive
                      )
                    }
                  >
                    <Button variant="ghost" className={styles.navButton}>
                      <Icon className={styles.navIcon} strokeWidth={2} />
                    </Button>
                    <span className={styles.navTooltip}>{label}</span>
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

        <main
          className={cn(
            styles.main,
            lessonEditorLayout && styles.mainLessonEditor
          )}
        >
          <div
            className={cn(
              styles.pageShell,
              isFullBleedAppPage(pathname) && styles.pageShellBleed,
              lessonEditorLayout && styles.pageShellLessonEditor
            )}
          >
            <QueryErrorResetBoundary>
              {({ reset }) => (
                <ErrorBoundary
                  onReset={reset}
                  FallbackComponent={ContentErrorFallback}
                >
                  <Suspense
                    fallback={
                      <div className={styles.outletSuspenseFallback}>
                        <Spinner size="lg" />
                      </div>
                    }
                  >
                    <Outlet />
                  </Suspense>
                </ErrorBoundary>
              )}
            </QueryErrorResetBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}
