import { type ReactNode } from 'react';
import type { UserRole } from '@shared/lib/rbac/roles';

export type AppRoute = {
  path?: string;
  index?: boolean;
  element: ReactNode;
  protected?: boolean;
  publicOnly?: boolean;
  roles?: UserRole[];
  children?: AppRoute[];
};
