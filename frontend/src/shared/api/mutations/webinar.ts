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
  return useMutation({
    mutationFn: () => webinarApi.startRecording(courseSlug, lessonSlug),
    onSuccess: () => {
      notifySuccess({ title: 'Запись началась' });
    },
    onError: (err) => handleWebinarError(err, 'webinarRecording'),
  });
}

export function useWhiteboardPdf(courseSlug: string, lessonSlug: string) {
  return useMutation({
    mutationFn: (screenshots: Blob[]) =>
      webinarApi.whiteboardPdf(courseSlug, lessonSlug, screenshots),
    onError: (err) => handleWebinarError(err, 'webinarWhiteboardPdf'),
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
