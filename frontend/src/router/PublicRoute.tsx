import { Navigate } from 'react-router-dom';
import { useAuth } from '../shared/hooks/useAuth';
import React from 'react';

export const PublicRoute = ({ children }: { children: React.JSX.Element }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Загрузка...</div>;
  }

  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  return children;
};