import { Suspense, useEffect } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { Outlet, Link, NavLink, useLocation } from 'react-router-dom';
import { House, ShoppingBag, Calendar, BookOpenCheck , BarChart2, SquareTerminal } from 'lucide-react';
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
import { useRole } from '@shared/lib/rbac';

import styles from './AppLayout.module.css';

function isFullBleedAppPage(pathname: string) {
  return pathname.endsWith('/webinar') || pathname.includes('/lesson/preview');
}

function isLessonEditorPage(pathname: string) {
  return pathname.includes('/courses/') && pathname.endsWith('/edit');
}

function getUserInitials(firstName?: string | null, lastName?: string | null): string {
  const first = firstName?.trim().charAt(0) ?? '';
  const last = lastName?.trim().charAt(0) ?? '';
  return (first + last).toUpperCase() || 'U';
}


export default function AppLayout() {
  const { pathname } = useLocation();
  const lessonEditorLayout = isLessonEditorPage(pathname);
  const hasToken = tokenService.hasToken();
  const { hasAny, role } = useRole();
  const canSeeStats = hasAny('teacher', 'moderator');
  const isModerator = role === 'moderator';
  const { data: user } = useProfile(hasToken);

  const { data: cart } = useCart();
  const cartHasItems = (cart?.courses?.length ?? 0) > 0;

  const initials = getUserInitials(user?.first_name, user?.last_name);

  const setInitial = useNotificationStore((s) => s.setInitial);

  useEffect(() => {
    if (hasToken && user) {
      console.log('[notifications:rest] initial fetch start');
      void notificationsApi
        .getAll()
        .then((response) => {
          console.log('[notifications:rest] initial fetch success', {
            count: response.results.length,
            has_more: response.has_more,
            ids: response.results.map((n) => n.id),
          });
          const mapped = response.results.map((n) => ({
            id: n.id,
            title: n.title,
            message: n.message,
            notification_type: n.notification_type,
            is_read: n.is_read,
            created_at: new Date(n.created_at),
          }));
          setInitial(mapped, response.has_more);
        })
        .catch((err) => {
          console.error('[notifications:rest] initial fetch failed', err);
          setInitial([], false);
        })
        .finally(() => {
          console.log('[notifications:rest] initial fetch done, connect SSE');
          connectNotificationSSE();
        });
      return;
    }

    console.log('[notifications:rest] no user/token, disconnect SSE');
    disconnectNotificationSSE();
    return () => {
      disconnectNotificationSSE();
    };
  }, [hasToken, user]);

  const navItems = [
    { href: '/app', label: 'Домашняя', icon: House, id: 'home' },
    { href: '/app/store', label: 'Магазин', icon: ShoppingBag, id: 'upload' },
    { href: '/app/schedule', label: 'Расписание', icon: Calendar, id: 'schedule' },
    { href: '/app/homeworks', label: 'Задания', icon: BookOpenCheck, id: 'distribute' },
  ];

  const navBottomItems = [
    ...(canSeeStats
      ? [{ href: '/app/statistics', label: 'Статистика', icon: BarChart2, id: 'statistics' }]
      : []),
    ...(isModerator
      ? [{ href: '/app/admin', label: 'Админ-панель', icon: SquareTerminal, id: 'admin' }]
      : []),
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
              {navItems.map(({ href, label, icon: Icon, id }) => (
                <NavLink
                  key={href}
                  to={href}
                  end={href === '/app'}
                  onPointerEnter={() => prefetchAppSidebarHref(href)}
                  onFocus={() => prefetchAppSidebarHref(href)}
                  className={({ isActive }) =>
                    cn(styles.navLink, styles[id], isActive && styles.navLinkActive)
                  }
                >
                  <Button variant="ghost" className={styles.navButton}>
                    <Icon className={styles.navIcon} strokeWidth={2} />
                  </Button>
                  <span className={styles.navTooltip}>{label}</span>
                </NavLink>
              ))}
            </nav>
          </div>
          {navBottomItems.length > 0 && (
            <nav className={cn(styles.nav, styles.navBottom)}>
              {navBottomItems.map(({ href, label, icon: Icon, id }) => (
                <NavLink
                  key={href}
                  to={href}
                  onPointerEnter={() => prefetchAppSidebarHref(href)}
                  onFocus={() => prefetchAppSidebarHref(href)}
                  className={({ isActive }) =>
                    cn(styles.navLink, styles[id], isActive && styles.navLinkActive)
                  }
                >
                  <Button variant="ghost" className={styles.navButton}>
                    <Icon className={styles.navIcon} strokeWidth={2} />
                  </Button>
                  <span className={styles.navTooltip}>{label}</span>
                </NavLink>
              ))}
            </nav>
          )}
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
