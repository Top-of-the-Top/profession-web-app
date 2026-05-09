import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../interceptor';
import { adminKeys, type AdminCourse, type AdminTeacher, type AdminTeacherInvite } from '../queries/adminPanel';
import { notifySuccess, notifyError } from '@shared/lib/sileo/notify';

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
      starts_at?: string | null;
      duration_weeks?: number | null;
      min_age?: number | null;
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
    mutationFn: (payload: Partial<{ title: string; sub_title: string; description: string; price: number }>) =>
      apiClient.request<AdminCourse>(`/api/v1/courses/${slug}/`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      notifySuccess({ title: 'Курс обновлён' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
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
    onSuccess: () => {
      notifySuccess({ title: 'Курс опубликован' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось опубликовать курс', description: errMsg(err) });
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
    onSuccess: () => {
      notifySuccess({ title: 'Курс снят с публикации' });
      void qc.invalidateQueries({ queryKey: adminKeys.courses() });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось снять курс с публикации', description: errMsg(err) });
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
