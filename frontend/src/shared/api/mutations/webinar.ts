import { useMutation, useQueryClient } from '@tanstack/react-query';
import { webinarApi } from '../webinarApi';
import { courseKeys } from '../queries/courses';
import { notifySuccess, notifyError } from '@shared/lib/sileo/notify';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { messageForApiFailure } from '@shared/lib/sileo/notify';
import type { ApiFailureScene } from '@shared/lib/api/backendApiMessages';

function handleWebinarError(err: unknown, scene: ApiFailureScene) {
  const parsed = parseApiError(err);
  if (parsed) {
    const m = messageForApiFailure(scene, parsed.status, parsed.body);
    notifyError({ title: m.title, description: m.description });
    return;
  }
  notifyError({ title: 'Ошибка', description: 'Повторите попытку.' });
}

export function useStartWebinar(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => webinarApi.start(courseSlug, lessonSlug),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
    },
    onError: (err) => handleWebinarError(err, 'webinarStart'),
  });
}

export function useStartRecording(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => webinarApi.startRecording(courseSlug, lessonSlug),
    onSuccess: () => {
      notifySuccess({
        title: 'Запись началась',
        description: 'На экране у всех участников отображается индикатор записи.',
      });
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
    },
    onError: (err) => handleWebinarError(err, 'webinarRecording'),
  });
}

export function useStopRecording(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => webinarApi.stopRecording(courseSlug, lessonSlug),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
      notifySuccess({ title: 'Запись остановлена' });
    },
    onError: (err) => handleWebinarError(err, 'webinarRecordingStop'),
  });
}

export function useUploadRecordingPdf(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      recordingId,
      screenshots,
    }: {
      recordingId: string;
      screenshots: Blob[];
    }) =>
      webinarApi.uploadRecordingPdf(
        courseSlug,
        lessonSlug,
        recordingId,
        screenshots,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
    },
    onError: (err) => handleWebinarError(err, 'recordingPdfUpload'),
  });
}

export function useUploadFinalPdf(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ screenshots }: { screenshots: Blob[] }) =>
      webinarApi.uploadFinalPdf(courseSlug, lessonSlug, screenshots),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
    },
    onError: (err) => handleWebinarError(err, 'recordingPdfUpload'),
  });
}

export function useDeleteRecordingPdf(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recordingId: string) =>
      webinarApi.deleteRecordingPdf(courseSlug, lessonSlug, recordingId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
      notifySuccess({ title: 'PDF удален' });
    },
    onError: (err) => handleWebinarError(err, 'recordingPdfDelete'),
  });
}

export function useDeleteRecording(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recordingId: string) =>
      webinarApi.deleteRecording(courseSlug, lessonSlug, recordingId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
      notifySuccess({ title: 'Запись удалена' });
    },
    onError: (err) => handleWebinarError(err, 'recordingDelete'),
  });
}

export function useStopWebinar(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => webinarApi.stop(courseSlug, lessonSlug),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: courseKeys.lesson(courseSlug, lessonSlug),
      });
    },
    onError: (err) => handleWebinarError(err, 'webinarStop'),
  });
}
