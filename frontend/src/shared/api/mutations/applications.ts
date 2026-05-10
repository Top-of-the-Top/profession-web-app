import { useMutation, useQueryClient } from '@tanstack/react-query';
import { applicationApi } from '../applicationApi';
import { applicationKeys } from '../queries/applications';
import { courseKeys } from '../queries/courses';
import { notifySuccess, notifyError } from '@shared/lib/sileo/notify';

function errMsg(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

export function useApplyToCourse(courseSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => applicationApi.apply(courseSlug),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: courseKeys.bySlug(courseSlug) });
    },
    onError: (err) => {
      const msg = errMsg(err);
      if (msg.includes('API_ERROR_409')) {
        notifyError({ title: 'Заявка уже подана' });
        return;
      }
      notifyError({ title: 'Не удалось подать заявку', description: msg });
    },
  });
}

export function useWithdrawApplication(courseSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => applicationApi.withdraw(courseSlug),
    onSuccess: () => {
      notifySuccess({ title: 'Заявка отозвана' });
      void qc.invalidateQueries({ queryKey: courseKeys.bySlug(courseSlug) });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось отозвать заявку', description: errMsg(err) });
    },
  });
}

export function useApproveApplication(courseSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) =>
      applicationApi.approve(courseSlug, applicationId),
    onSuccess: () => {
      notifySuccess({ title: 'Заявка одобрена' });
      void qc.invalidateQueries({ queryKey: applicationKeys.list(courseSlug) });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось одобрить заявку', description: errMsg(err) });
    },
  });
}

export function useRejectApplication(courseSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) =>
      applicationApi.reject(courseSlug, applicationId),
    onSuccess: () => {
      notifySuccess({ title: 'Заявка отклонена' });
      void qc.invalidateQueries({ queryKey: applicationKeys.list(courseSlug) });
    },
    onError: (err) => {
      notifyError({ title: 'Не удалось отклонить заявку', description: errMsg(err) });
    },
  });
}
