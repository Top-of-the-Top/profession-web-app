import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  courseApi,
  type CourseContentType,
  type CoursePatchPayload,
  type CourseHomeResponse,
  type LessonCreatePayload,
} from '../courseApi';
import { courseKeys } from '../queries/courses';
import { notifySuccess, notifyError } from '@shared/lib/sileo/notify';

function errMsg(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

export function useCreateLesson(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: LessonCreatePayload) =>
      courseApi.createLesson(courseSlug, payload),
    onSuccess: () => {
      notifySuccess({ title: 'Урок создан' });
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(courseSlug) });
    },
    onError: (err) => {
      notifyError({
        title: 'Не удалось создать урок',
        description: errMsg(err),
      });
    },
  });
}

export function useToggleLessonType(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      lessonSlug,
      currentType,
    }: {
      lessonSlug: string;
      currentType: CourseContentType | undefined;
    }) => {
      const newType: CourseContentType =
        currentType === 'published' ? 'draft' : 'published';
      return courseApi.patchLesson(courseSlug, lessonSlug, { type: newType });
    },
    onMutate: async ({ lessonSlug, currentType }) => {
      await qc.cancelQueries({
        queryKey: courseKeys.courseHome(courseSlug),
      });
      const prev = qc.getQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
      );

      qc.setQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
        (old) => {
          if (!old) return old;
          const newType: CourseContentType =
            currentType === 'published' ? 'draft' : 'published';
          return {
            ...old,
            content: old.content.map((section) => ({
              ...section,
              lessons: section.lessons.map((l) =>
                l.slug === lessonSlug ? { ...l, type: newType } : l,
              ),
            })),
          };
        },
      );

      return { prev };
    },
    onError: (err, _vars, context) => {
      if (context?.prev) {
        qc.setQueryData(courseKeys.courseHome(courseSlug), context.prev);
      }
      notifyError({
        title: 'Не удалось обновить статус',
        description: errMsg(err),
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(courseSlug) });
    },
  });
}

export function useDeleteLesson(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (lessonSlug: string) =>
      courseApi.deleteLesson(courseSlug, lessonSlug),
    onSuccess: () => {
      notifySuccess({ title: 'Урок удалён' });
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(courseSlug) });
    },
    onError: (err) => {
      notifyError({
        title: 'Не удалось удалить урок',
        description: errMsg(err),
      });
    },
  });
}

export function usePatchCourse(slug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: CoursePatchPayload) =>
      courseApi.patchCourse(slug, payload),
    onSuccess: () => {
      notifySuccess({ title: 'Курс обновлён' });
      void qc.invalidateQueries({ queryKey: courseKeys.bySlug(slug) });
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(slug) });
    },
    onError: (err) => {
      notifyError({
        title: 'Не удалось обновить курс',
        description: errMsg(err),
      });
    },
  });
}
