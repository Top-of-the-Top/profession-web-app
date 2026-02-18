// src/widgets/admin-layout/index.tsx
import { useState, useEffect } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import {
  Upload,
  Edit,
  Users,
  Trash2,
  ArrowRight,
  AlertCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button, Alert, AlertDescription, AlertTitle } from "../../../shared/ui";
import { cn } from "../../../shared/lib/utils";

import styles from "./styles.module.css";


type ErrorType =
  | "forbidden"
  | "server_error"
  | "network_error"
  | "unauthorized"
  | null;

export default function AdminLayout() {
  const location = useLocation();

  const navItems = [
    { href: "/admin/home", label: "Главная", icon: ArrowRight, id: "home" },
    {
      href: "/admin/upload",
      label: "Загрузить таблицу",
      icon: Upload,
      id: "upload",
    },
    {
      href: "/admin/modify",
      label: "Внести изменения",
      icon: Edit,
      id: "modify",
    },
    {
      href: "/admin/distribute",
      label: "Распределить одиночек",
      icon: Users,
      id: "distribute",
    },
    {
      href: "/admin/clear",
      label: "Очистить таблицу",
      icon: Trash2,
      id: "delete",
    },
  ];

  return (
    <div className={styles.container}>
      <div className={styles.sidebar}>
        <div className={styles.navContainer}>
          <nav className={styles.nav}>
            {navItems.map(({ href, label, icon: Icon, id }) => {
              const isActive = location.pathname === href;

              return (
                <Link
                  key={href}
                  to={href}
                  className={cn(styles.navLink, styles[id])}
                >
                  <Button
                    variant='secondary'
                    className={styles.navButton}
                  >
                    <Icon className={styles.navIcon} strokeWidth={1.5} />
                    <span>{label}</span>
                  </Button>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className={styles.statsSection}>
          {stats.status === "connecting" && (
            <div className={styles.loading}>Подключение к серверу...</div>
          )}

          {stats.status === "connected" && (
            <>
              
            </>
          )}

          {stats.status === "disconnected" && (
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


          {stats.status === "error" && (
            <>
              <Alert variant="destructive">
                <AlertCircle />
                <AlertTitle>Ошибка подключения</AlertTitle>
                <AlertDescription>{stats.error}</AlertDescription>
              </Alert>
              <Button onClick={() => {}}>Переподключиться</Button>
            </>
          )}
        </div>
      </div>

      <main className={styles.main}>
        <div className={styles.adminWrapper}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
