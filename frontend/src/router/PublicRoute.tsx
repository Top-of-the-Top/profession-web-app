// router/PublicRoute.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { Spinner } from '@shared/ui';

export const PublicRoute = ({ children }: { children: React.JSX.Element }) => {
  const { user, isLoading } = useUserStore();

  if (isLoading) {
    return <Spinner full />;
  }

  if (user) {
    return <Navigate to="/app/store" replace />;
  }

  return children;
};