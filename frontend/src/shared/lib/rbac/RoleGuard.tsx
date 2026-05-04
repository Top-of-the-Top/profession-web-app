import { Navigate } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { Spinner } from '@shared/ui';
import type { UserRole } from './roles';

interface RoleGuardProps {
  allowed: UserRole[];
  redirectTo?: string;
  children: React.JSX.Element;
}

export function RoleGuard({
  allowed,
  redirectTo = '/app/not-authorized',
  children,
}: RoleGuardProps) {
  const role = useUserStore((s) => s.role);
  const isAuthChecked = useUserStore((s) => s.isAuthChecked);
  const isLoading = useUserStore((s) => s.isLoading);

  if (!isAuthChecked || isLoading) {
    return <Spinner full />;
  }

  if (role === null) {
    return <Navigate to={redirectTo} replace />;
  }

  if (!allowed.includes(role)) {
    return <Navigate to={redirectTo} replace />;
  }

  return children;
}
