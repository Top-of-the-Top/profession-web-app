import { useUserStore } from '@entities/user/model/userStore';
import { ROLES, type UserRole } from './roles';

export function useRole() {
  const role = useUserStore((s) => s.role);
  const userId = useUserStore((s) => s.userId);

  return {
    role,
    userId,
    is: {
      student: role === ROLES.student,
      teacher: role === ROLES.teacher,
      moderator: role === ROLES.moderator,
    },
    hasAny: (...roles: UserRole[]) => role !== null && roles.includes(role),
  };
}
