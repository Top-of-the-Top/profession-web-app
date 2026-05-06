import { useQuery } from '@tanstack/react-query';
import { courseApi } from '../courseApi';

export const courseKeys = {
  all: ['courses'] as const,
  store: () => [...courseKeys.all, 'store'] as const,
  home: () => [...courseKeys.all, 'home'] as const,
  bySlug: (slug: string) => [...courseKeys.all, 'detail', slug] as const,
  courseHome: (slug: string) => [...courseKeys.all, 'home', slug] as const,
  lesson: (courseSlug: string, lessonSlug: string) =>
    [...courseKeys.all, courseSlug, 'lessons', lessonSlug] as const,
  homework: (courseSlug: string, lessonSlug: string, homeworkSlug: string) =>
    [...courseKeys.all, courseSlug, 'lessons', lessonSlug, 'homework', homeworkSlug] as const,
  homeworkAttempt: (homeworkSlug: string) =>
    [...courseKeys.all, 'homework-attempt', homeworkSlug] as const,
  homeworkAttemptsByCourse: (courseSlug: string) =>
    [...courseKeys.all, courseSlug, 'attempts'] as const,
  homeworkAttemptReview: (courseSlug: string, attemptId: string) =>
    [...courseKeys.all, courseSlug, 'attempts', attemptId] as const,
};

export function useCourses() {
  return useQuery({
    queryKey: courseKeys.store(),
    queryFn: () => courseApi.getCourses(),
  });
}

export function useCoursesForHome() {
  return useQuery({
    queryKey: courseKeys.home(),
    queryFn: () => courseApi.getCoursesForAppHome(),
  });
}

export function useCourseBySlug(slug: string | undefined) {
  return useQuery({
    queryKey: courseKeys.bySlug(slug!),
    queryFn: () => courseApi.getCourseBySlug(slug!),
    enabled: !!slug,
  });
}

export function useCourseHomeBySlug(slug: string | undefined) {
  return useQuery({
    queryKey: courseKeys.courseHome(slug!),
    queryFn: () => courseApi.getCourseHomeBySlug(slug!),
    enabled: !!slug,
  });
}

export function useLessonBySlug(
  courseSlug: string | undefined,
  lessonSlug: string | undefined,
  opts?: { editorMode?: boolean },
) {
  return useQuery({
    queryKey: courseKeys.lesson(courseSlug!, lessonSlug!),
    queryFn: () => courseApi.getLessonBySlug(courseSlug!, lessonSlug!),
    enabled: !!courseSlug && !!lessonSlug,
    // In editor mode never auto-refetch — would clobber unsaved work
    staleTime: opts?.editorMode ? Infinity : 30_000,
    refetchOnWindowFocus: opts?.editorMode ? false : true,
  });
}

export function useHomeworkDetail(
  courseSlug: string | undefined,
  lessonSlug: string | undefined,
  homeworkSlug: string | undefined,
  opts?: { editorMode?: boolean },
) {
  return useQuery({
    queryKey: courseKeys.homework(courseSlug!, lessonSlug!, homeworkSlug!),
    queryFn: () => courseApi.getHomeworkDetail(courseSlug!, lessonSlug!, homeworkSlug!),
    enabled: !!courseSlug && !!lessonSlug && !!homeworkSlug,
    staleTime: opts?.editorMode ? Infinity : 30_000,
    refetchOnWindowFocus: opts?.editorMode ? false : true,
  });
}

export function useHomeworkAttempt(
  courseSlug: string | undefined,
  homeworkSlug: string | undefined,
) {
  return useQuery({
    queryKey: courseKeys.homeworkAttempt(homeworkSlug!),
    queryFn: () => courseApi.getHomeworkAttempt(courseSlug!, homeworkSlug!),
    enabled: !!courseSlug && !!homeworkSlug,
  });
}

export function useHomeworkAttemptsByCourse(courseSlug: string | undefined) {
  return useQuery({
    queryKey: courseKeys.homeworkAttemptsByCourse(courseSlug!),
    queryFn: () => courseApi.getHomeworkAttemptsByCourse(courseSlug!),
    enabled: !!courseSlug,
  });
}

export function useHomeworkAttemptForReview(
  courseSlug: string | undefined,
  attemptId: string | undefined,
) {
  return useQuery({
    queryKey: courseKeys.homeworkAttemptReview(courseSlug!, attemptId!),
    queryFn: () => courseApi.getHomeworkAttemptForReview(courseSlug!, attemptId!),
    enabled: !!courseSlug && !!attemptId,
  });
}
