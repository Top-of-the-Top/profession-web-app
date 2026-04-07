import { Navigate } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
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

  if (role === null) return children;

  if (!allowed.includes(role)) {
    return <Navigate to={redirectTo} replace />;
  }

  return children;
}
