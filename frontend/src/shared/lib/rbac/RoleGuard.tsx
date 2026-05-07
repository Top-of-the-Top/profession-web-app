import { Navigate, useLocation } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { Spinner } from '@shared/ui';
import type { UserRole } from './roles';
import { peekAuthLogoutReason } from '@shared/lib/auth/logoutReason';

interface RoleGuardProps {
  allowed: UserRole[];
  redirectTo?: string;
  children: React.JSX.Element;
}

export function RoleGuard({
  allowed,
  redirectTo,
  children,
}: RoleGuardProps) {
  const location = useLocation();
  const user = useUserStore((s) => s.user);
  const role = useUserStore((s) => s.role);
  const isAuthChecked = useUserStore((s) => s.isAuthChecked);
  const isLoading = useUserStore((s) => s.isLoading);

  if (!isAuthChecked || isLoading) {
    return <Spinner full />;
  }

  if (!user || role === null) {
    const authReason = peekAuthLogoutReason();
    return (
      <Navigate
        to="/login"
        state={{ from: location, authReason }}
        replace
      />
    );
  }

  if (!allowed.includes(role)) {
    return <Navigate to={redirectTo ?? '/app'} replace />;
  }

  return children;
}
