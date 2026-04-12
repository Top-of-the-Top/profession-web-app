import { type ReactNode } from 'react';
import { useRole } from './useRole';
import type { UserRole } from './roles';

interface RoleCheckContext {
  role: UserRole;
  userId: number | null;
}

interface CanProps {
  role?: UserRole | UserRole[];
  check?: (ctx: RoleCheckContext) => boolean;
  fallback?: ReactNode;
  children: ReactNode;
}

export function Can({ role: allowed, check, fallback = null, children }: CanProps) {
  const { role, userId } = useRole();

  if (role === null) return <>{fallback}</>;

  if (allowed) {
    const roles = Array.isArray(allowed) ? allowed : [allowed];
    if (!roles.includes(role)) return <>{fallback}</>;
  }

  if (check && !check({ role, userId })) return <>{fallback}</>;

  return <>{children}</>;
}
