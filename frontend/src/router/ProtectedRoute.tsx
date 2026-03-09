// router/ProtectedRoute.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useUserStore } from '../entities/user/model/userStore';

export const ProtectedRoute = ({ children }: { children: React.JSX.Element }) => {
  const { user, isLoading, isAuthChecked } = useUserStore();
  const location = useLocation();

  // Пока не завершили первичную проверку авторизации — показываем лоадер
  if (!isAuthChecked || isLoading) {
    return <div>Загрузка...</div>;
  }

  if (!user) {
    return (
      <Navigate
        to="/"
        state={{ from: location }}
        replace
      />
    );
  }

  return children;
};