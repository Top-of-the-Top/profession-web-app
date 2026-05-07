import { useQuery } from '@tanstack/react-query';
import { internalLandingApi } from '@shared/api/landingApi';

export const landingKeys = {
  courses: ['landing', 'courses'] as const,
};

export function useLandingCourses() {
  return useQuery({
    queryKey: landingKeys.courses,
    queryFn: () => internalLandingApi.getCourses(),
    staleTime: Infinity,
  });
}
