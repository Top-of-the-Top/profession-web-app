import { useQuery } from '@tanstack/react-query';
import { webinarApi } from '../webinarApi';

export const webinarKeys = {
  all: ['webinar'] as const,
  join: (courseSlug: string, lessonSlug: string) =>
    [...webinarKeys.all, 'join', courseSlug, lessonSlug] as const,
  recorderJoin: (courseSlug: string, lessonSlug: string, token: string) =>
    [...webinarKeys.all, 'recorder-join', courseSlug, lessonSlug, token] as const,
};

export function useWebinarJoin(
  courseSlug: string | undefined,
  lessonSlug: string | undefined,
) {
  return useQuery({
    queryKey: webinarKeys.join(courseSlug!, lessonSlug!),
    queryFn: () => webinarApi.join(courseSlug!, lessonSlug!),
    enabled: !!courseSlug && !!lessonSlug,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    retry: false,
  });
}

export function useRecorderJoin(
  courseSlug: string | undefined,
  lessonSlug: string | undefined,
  token: string | null | undefined,
) {
  return useQuery({
    queryKey: webinarKeys.recorderJoin(courseSlug!, lessonSlug!, token ?? ''),
    queryFn: () => webinarApi.recorderJoin(courseSlug!, lessonSlug!, token!),
    enabled: !!courseSlug && !!lessonSlug && !!token,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    retry: false,
  });
}
