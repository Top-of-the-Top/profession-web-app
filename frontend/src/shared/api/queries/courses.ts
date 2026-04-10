import { useQuery } from '@tanstack/react-query';
import { courseApi } from '../courseApi';

export const courseKeys = {
  all: ['courses'] as const,
  store: () => [...courseKeys.all, 'store'] as const,
  home: () => [...courseKeys.all, 'home'] as const,
  bySlug: (slug: string) => [...courseKeys.all, 'detail', slug] as const,
  courseHome: (slug: string) => [...courseKeys.all, 'home', slug] as const,
  lessons: (courseSlug: string) =>
    [...courseKeys.all, courseSlug, 'lessons'] as const,
  lesson: (courseSlug: string, lessonSlug: string) =>
    [...courseKeys.all, courseSlug, 'lessons', lessonSlug] as const,
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

export function useLessons(courseSlug: string | undefined) {
  return useQuery({
    queryKey: courseKeys.lessons(courseSlug!),
    queryFn: () => courseApi.getLessons(courseSlug!),
    enabled: !!courseSlug,
  });
}

export function useLessonBySlug(
  courseSlug: string | undefined,
  lessonSlug: string | undefined,
) {
  return useQuery({
    queryKey: courseKeys.lesson(courseSlug!, lessonSlug!),
    queryFn: () => courseApi.getLessonBySlug(courseSlug!, lessonSlug!),
    enabled: !!courseSlug && !!lessonSlug,
  });
}
