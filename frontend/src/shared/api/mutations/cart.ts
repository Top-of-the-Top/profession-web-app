import { useMutation, useQueryClient } from '@tanstack/react-query';
import { cartApi, type CartResponse } from '../cartApi';
import { cartKeys } from '../queries/cart';
import { courseKeys } from '../queries/courses';
import type { CourseApiAnswer, CourseBySlugAnswer, CourseDTO } from '../courseApi';

export function useAddToCart() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => cartApi.addCourse(slug),
    onMutate: async (slug) => {
      await qc.cancelQueries({ queryKey: cartKeys.all });
      const prev = qc.getQueryData<CartResponse>(cartKeys.all);

      qc.setQueryData<CartResponse>(cartKeys.all, (old) => {
        if (!old || old.courses.some((course) => course.slug === slug)) {
          return old;
        }

        const storeCourses = qc.getQueryData<CourseApiAnswer>(courseKeys.store())?.data ?? [];
        const courseBySlug = qc.getQueryData<CourseBySlugAnswer>(courseKeys.bySlug(slug))?.course;
        const candidate: CourseDTO | undefined =
          storeCourses.find((course) => course.slug === slug) ?? courseBySlug;

        if (!candidate) {
          return old;
        }

        return {
          ...old,
          courses: [...old.courses, candidate],
        };
      });

      return { prev };
    },
    onError: (_err, _slug, context) => {
      if (context?.prev) {
        qc.setQueryData<CartResponse>(cartKeys.all, context.prev);
      }
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: cartKeys.all });
    },
  });
}

export function useRemoveFromCart() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => cartApi.removeCourse(slug),
    onMutate: async (slug) => {
      await qc.cancelQueries({ queryKey: cartKeys.all });
      const prev = qc.getQueryData<CartResponse>(cartKeys.all);

      qc.setQueryData<CartResponse>(cartKeys.all, (old) =>
        old
          ? { ...old, courses: old.courses.filter((c) => c.slug !== slug) }
          : old,
      );

      return { prev };
    },
    onError: (_err, _slug, context) => {
      if (context?.prev) {
        qc.setQueryData<CartResponse>(cartKeys.all, context.prev);
      }
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: cartKeys.all });
    },
  });
}
