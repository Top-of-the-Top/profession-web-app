// router/ProtectedRoute.tsx
import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useUserStore } from '../entities/user/model/userStore';
import { tokenService } from '../shared/lib/auth/tokenService';
import { Spinner } from '../shared/ui';

export const ProtectedRoute = ({ children }: { children: React.JSX.Element }) => {
  const { user, isLoading, isAuthChecked, fetchUser } = useUserStore();
  const location = useLocation();
  const hasToken = tokenService.hasToken();

  useEffect(() => {
    if (hasToken && !isAuthChecked && !isLoading) {
      console.info('[route] ProtectedRoute -> fetchUser');
      void fetchUser();
    }
  }, [fetchUser, hasToken, isAuthChecked, isLoading]);

  useEffect(() => {
    console.info('[route] ProtectedRoute state', {
      hasToken,
      isAuthChecked,
      isLoading,
      hasUser: Boolean(user),
      pathname: location.pathname,
    });
  }, [hasToken, isAuthChecked, isLoading, location.pathname, user]);

  if (hasToken && (!isAuthChecked || isLoading)) {
    return <Spinner full />;
  }

  if (!hasToken || !user) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    );
  }

  return children;
};