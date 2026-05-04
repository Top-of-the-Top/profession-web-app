// router/ProtectedRoute.tsx
import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { peekAuthLogoutReason } from '@shared/lib/auth/logoutReason';
import { tokenService } from '@shared/lib/auth/tokenService';
import { Spinner } from '@shared/ui';

export const ProtectedRoute = ({ children }: { children: React.JSX.Element }) => {
  const { user, isLoading, isAuthChecked, fetchUser } = useUserStore();
  const location = useLocation();
  const hasToken = tokenService.hasToken();

  useEffect(() => {
    if (hasToken && !isAuthChecked && !isLoading) {
      void fetchUser();
    }
  }, [fetchUser, hasToken, isAuthChecked, isLoading]);


  if (hasToken && (!isAuthChecked || isLoading)) {
    return <Spinner full />;
  }

  if (!hasToken || !user) {
    const authReason = peekAuthLogoutReason();
    return (
      <Navigate
        to="/login"
        state={{ from: location, authReason }}
        replace
      />
    );
  }

  return children;
};