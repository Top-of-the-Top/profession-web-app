import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  courseApi,
  type AppCourseLesson,
  type AppCourseSection,
  type CourseContentType,
  type CoursePatchPayload,
  type CourseHomeResponse,
  type Lesson,
  type LessonCreatePayload,
  type SectionCreatePayload,
  type SectionPatchPayload,
  type SectionRecord,
} from '../courseApi';
import { courseKeys } from '../queries/courses';
import { notifySuccess, notifyError } from '@shared/lib/sileo/notify';

function errMsg(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

function optimisticKey(): string {
  return `optimistic:${crypto.randomUUID()}`;
}

function sectionRecordToAppSection(record: SectionRecord): AppCourseSection {
  return {
    section_id: String(record.section_id),
    section_number: record.section_number,
    title: record.title,
    slug: record.slug,
    lessons: [],
    type: record.type,
  };
}

function lessonToAppLesson(lesson: Lesson): AppCourseLesson {
  return {
    lesson_id: String(lesson.lesson_id),
    lesson_number: lesson.lesson_number,
    title: lesson.title,
    slug: lesson.slug,
    type: lesson.type,
  };
}

export function useCreateSection(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: SectionCreatePayload) =>
      courseApi.createSection(courseSlug, payload),
    onMutate: async (payload) => {
      await qc.cancelQueries({
        queryKey: courseKeys.courseHome(courseSlug),
      });
      const prev = qc.getQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
      );
      const tempSectionId = optimisticKey();
      qc.setQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
        (old) => {
          if (!old) return old;
          const maxNum = old.content.reduce(
            (m, s) => Math.max(m, s.section_number),
            0,
          );
          const optimistic: AppCourseSection = {
            section_id: tempSectionId,
            section_number: maxNum + 1,
            title: payload.title,
            slug: undefined,
            lessons: [],
            type: 'draft',
          };
          return { ...old, content: [...old.content, optimistic] };
        },
      );
      return { prev, tempSectionId };
    },
    onSuccess: (record, _payload, context) => {
      notifySuccess({ title: 'Раздел создан' });
      const mapped = sectionRecordToAppSection(record);
      qc.setQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            content: old.content.map((section) =>
              section.section_id === context?.tempSectionId
                ? { ...mapped, lessons: section.lessons }
                : section,
            ),
          };
        },
      );
    },
    onError: (err, _payload, context) => {
      if (context?.prev !== undefined) {
        qc.setQueryData(courseKeys.courseHome(courseSlug), context.prev);
      } else {
        void qc.invalidateQueries({
          queryKey: courseKeys.courseHome(courseSlug),
        });
      }
      notifyError({
        title: 'Не удалось создать раздел',
        description: errMsg(err),
      });
    },
  });
}

export function usePatchSection(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      sectionSlug,
      payload,
    }: {
      sectionSlug: string;
      payload: SectionPatchPayload;
    }) => courseApi.patchSection(courseSlug, sectionSlug, payload),
    onSuccess: () => {
      notifySuccess({ title: 'Раздел обновлён' });
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(courseSlug) });
    },
    onError: (err) => {
      notifyError({
        title: 'Не удалось обновить раздел',
        description: errMsg(err),
      });
    },
  });
}

export function useDeleteSection(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (sectionSlug: string) =>
      courseApi.deleteSection(courseSlug, sectionSlug),
    onSuccess: () => {
      notifySuccess({ title: 'Раздел удалён' });
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(courseSlug) });
    },
    onError: (err) => {
      notifyError({
        title: 'Не удалось удалить раздел',
        description: errMsg(err),
      });
    },
  });
}

export function useToggleSectionType(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      sectionSlug,
      currentType,
    }: {
      sectionSlug: string;
      currentType: CourseContentType | undefined;
    }) => {
      const newType: CourseContentType =
        currentType === 'published' ? 'draft' : 'published';
      return courseApi.patchSection(courseSlug, sectionSlug, { type: newType });
    },
    onMutate: async ({ sectionSlug, currentType }) => {
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
            content: old.content.map((section) =>
              section.slug === sectionSlug
                ? { ...section, type: newType }
                : section,
            ),
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
        title: 'Не удалось обновить статус раздела',
        description: errMsg(err),
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(courseSlug) });
    },
  });
}

export function useCreateLesson(courseSlug: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: LessonCreatePayload) =>
      courseApi.createLesson(courseSlug, payload),
    onMutate: async (payload) => {
      const sectionId = payload.section;
      if (!sectionId) {
        return {};
      }
      await qc.cancelQueries({
        queryKey: courseKeys.courseHome(courseSlug),
      });
      const prev = qc.getQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
      );
      const tempLessonId = optimisticKey();
      const pendingSlug = `pending-${crypto.randomUUID()}`;
      qc.setQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            content: old.content.map((section) => {
              if (section.section_id !== sectionId) return section;
              const maxNum = section.lessons.reduce(
                (m, l) => Math.max(m, l.lesson_number),
                0,
              );
              const optimisticLesson: AppCourseLesson = {
                lesson_id: tempLessonId,
                lesson_number: maxNum + 1,
                title: payload.title,
                slug: pendingSlug,
                type: 'draft',
              };
              return {
                ...section,
                lessons: [...section.lessons, optimisticLesson],
              };
            }),
          };
        },
      );
      return { prev, tempLessonId, sectionId };
    },
    onSuccess: (lesson, variables, context) => {
      notifySuccess({ title: 'Урок создан' });
      const sid = variables.section;
      if (!sid || !context?.tempLessonId) return;
      const appLesson = lessonToAppLesson(lesson);
      qc.setQueryData<CourseHomeResponse>(
        courseKeys.courseHome(courseSlug),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            content: old.content.map((section) =>
              section.section_id !== sid
                ? section
                : {
                    ...section,
                    lessons: section.lessons.map((l) =>
                      l.lesson_id === context.tempLessonId ? appLesson : l,
                    ),
                  },
            ),
          };
        },
      );
    },
    onError: (err, _variables, context) => {
      if (context?.prev !== undefined) {
        qc.setQueryData(courseKeys.courseHome(courseSlug), context.prev);
      } else if (context && 'tempLessonId' in context) {
        void qc.invalidateQueries({
          queryKey: courseKeys.courseHome(courseSlug),
        });
      }
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
