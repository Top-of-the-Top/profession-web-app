import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../interceptor';
import { courseApi } from '../courseApi/client';
import type { CoursePatchPayload } from '../courseApi/types';
import { adminKeys, type AdminCourse, type AdminTeacher, type AdminTeacherInvite } from '../queries/adminPanel';
import { courseKeys } from '../queries/courses';
import { notifySuccess, notifyError } from '@shared/lib/sileo/notify';

function adminCourseTypeFromApiStatus(status: unknown): AdminCourse['type'] {
  return typeof status === 'string' && status.trim().toLowerCase() === 'published'
    ? 'published'
    : 'draft';
}

function patchAdminCoursesCache(
  qc: ReturnType<typeof useQueryClient>,
  slug: string,
  nextType: AdminCourse['type'],
) {
  qc.setQueryData<AdminCourse[]>(adminKeys.courses(), (old) => {
    if (!old) return old;
    return old.map((c) => (c.slug === slug ? { ...c, type: nextType } : c));
  });
}

function errMsg(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

export function useCreateCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      title: string;
      sub_title: string;
      description: string;
      price: number;
      is_special?: boolean;
      starts_at?: string | null;
      duration_weeks?: number | null;
      min_age?: number | null;
      course_cover_asset_id?: string | null;
    }) =>
      apiClient.request<AdminCourse>('/api/v1/courses/', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      notifySuccess({ title: 'Курс создан' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось создать курс', description: errMsg(err) });
    },
  });
}

export function usePatchAdminCourse(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<CoursePatchPayload>) => courseApi.patchCourse(slug, payload),
    onSuccess: () => {
      notifySuccess({ title: 'Курс обновлён' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
      void qc.invalidateQueries({ queryKey: courseKeys.bySlug(slug) });
      void qc.invalidateQueries({ queryKey: courseKeys.courseHome(slug) });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось обновить курс', description: errMsg(err) });
    },
  });
}

export function useDeleteAdminCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      apiClient.request<void>(`/api/v1/courses/${slug}/`, { method: 'DELETE' }),
    onSuccess: () => {
      notifySuccess({ title: 'Курс удалён' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось удалить курс', description: errMsg(err) });
    },
  });
}

export function usePublishCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      apiClient.request<{ status: string }>(`/api/v1/admin-panel/courses/${slug}/publish/`, {
        method: 'POST',
      }),
    onSuccess: (data, slug) => {
      notifySuccess({ title: 'Курс опубликован' });
      patchAdminCoursesCache(qc, slug, adminCourseTypeFromApiStatus(data?.status));
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось опубликовать курс', description: errMsg(err) });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
  });
}

export function useUnpublishCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      apiClient.request<{ status: string }>(`/api/v1/admin-panel/courses/${slug}/unpublish/`, {
        method: 'POST',
      }),
    onSuccess: (data, slug) => {
      notifySuccess({ title: 'Курс снят с публикации' });
      patchAdminCoursesCache(qc, slug, adminCourseTypeFromApiStatus(data?.status));
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось снять курс с публикации', description: errMsg(err) });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
  });
}

export function useAddCourseAuthor(courseSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) =>
      apiClient.request<AdminTeacher[]>(
        `/api/v1/admin-panel/courses/${courseSlug}/add-author/?user_id=${userId}`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      notifySuccess({ title: 'Преподаватель добавлен' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось добавить преподавателя', description: errMsg(err) });
    },
  });
}

export function useRemoveCourseAuthor(courseSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) =>
      apiClient.request<AdminTeacher[]>(
        `/api/v1/admin-panel/courses/${courseSlug}/remove-author/?user_id=${userId}`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      notifySuccess({ title: 'Преподаватель снят с курса' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось снять преподавателя', description: errMsg(err) });
    },
  });
}

export function useSendInvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (email: string) =>
      apiClient.request<AdminTeacherInvite>('/api/v1/admin-panel/invites/send/', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),
    onSuccess: () => {
      notifySuccess({ title: 'Приглашение отправлено' });
      void qc.invalidateQueries({ queryKey: adminKeys.invites() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось отправить приглашение', description: errMsg(err) });
    },
  });
}
