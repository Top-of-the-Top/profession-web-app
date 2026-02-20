// src/widgets/admin-layout/index.tsx
import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Upload,
  Edit,
  Users,
  Trash2,
  ArrowRight,
  AlertCircle,
  ShoppingCart,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Alert,
  AlertDescription,
  AlertTitle,
} from '../../../shared/ui';
import { cn } from '../../../shared/lib/utils';

import styles from './AppLayout.module.css';

type ErrorType =
  | 'forbidden'
  | 'server_error'
  | 'network_error'
  | 'unauthorized'
  | null;

export default function AppLayout() {
  const location = useLocation();

  const navItems = [
    { href: '/app/home', label: 'Домашняя', icon: ArrowRight, id: 'home' },
    {
      href: '/app/upload',
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
          <Link className={styles.headerLink} to='/cart'><ShoppingCart width={'20px'} height={'20px'} /></Link>
          <Link to="profile" className={styles.headerLink}>
            <div className={styles.pfp}>
							{/* TODO: НУЖНО ПОЛУЧАТЬ ОТ СЕРВЕРА */}
              <img src="/ya.svg" alt="Profile" />
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
                const isActive = location.pathname === href;

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
                  <AlertDescription>{}</AlertDescription>
                </Alert>
                <Button onClick={() => {}}>Переподключиться</Button>
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
