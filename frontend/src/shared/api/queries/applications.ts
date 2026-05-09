import { useQuery } from '@tanstack/react-query';
import { applicationApi, type ApplicationStatus } from '../applicationApi';

export const applicationKeys = {
  all: ['applications'] as const,
  list: (courseSlug: string, status?: ApplicationStatus) =>
    [...applicationKeys.all, courseSlug, status ?? 'all'] as const,
};

export function useApplications(
  courseSlug: string | undefined,
  status?: ApplicationStatus,
) {
  return useQuery({
    queryKey: applicationKeys.list(courseSlug!, status),
    queryFn: () => applicationApi.list(courseSlug!, status),
    enabled: !!courseSlug,
  });
}
