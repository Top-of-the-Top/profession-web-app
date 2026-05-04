import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { CourseLessonDetail } from '../courseApi';
import { webinarApi } from '../webinarApi';
import { courseKeys } from '../queries/courses';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifySuccess,
} from '@shared/lib/sileo/notify';
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
  const lessonKey = courseKeys.lesson(courseSlug, lessonSlug);

  return useMutation({
    mutationFn: (recordingId: string) =>
      webinarApi.deleteRecordingPdf(courseSlug, lessonSlug, recordingId),
    onMutate: async (recordingId) => {
      await queryClient.cancelQueries({ queryKey: lessonKey });
      const prev = queryClient.getQueryData<CourseLessonDetail>(lessonKey);
      queryClient.setQueryData<CourseLessonDetail>(lessonKey, (old) => {
        if (!old) return old;
        return {
          ...old,
          recordings: old.recordings.map((r) =>
            r.recording_id === recordingId ? { ...r, whiteboard_pdf_url: '' } : r,
          ),
        };
      });
      return { prev };
    },
    onError: (err, _recordingId, context) => {
      if (context?.prev !== undefined) {
        queryClient.setQueryData(lessonKey, context.prev);
      }
      handleWebinarError(err, 'recordingPdfDelete');
    },
    onSuccess: () => {
      notifySuccess({ title: 'PDF удален' });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: lessonKey });
    },
  });
}

export function useDeleteRecording(courseSlug: string, lessonSlug: string) {
  const queryClient = useQueryClient();
  const lessonKey = courseKeys.lesson(courseSlug, lessonSlug);

  return useMutation({
    mutationFn: (recordingId: string) =>
      webinarApi.deleteRecording(courseSlug, lessonSlug, recordingId),
    onMutate: async (recordingId) => {
      await queryClient.cancelQueries({ queryKey: lessonKey });
      const prev = queryClient.getQueryData<CourseLessonDetail>(lessonKey);
      queryClient.setQueryData<CourseLessonDetail>(lessonKey, (old) => {
        if (!old) return old;
        return {
          ...old,
          recordings: old.recordings.filter((r) => r.recording_id !== recordingId),
        };
      });
      return { prev };
    },
    onError: (err, _recordingId, context) => {
      if (context?.prev !== undefined) {
        queryClient.setQueryData(lessonKey, context.prev);
      }
      handleWebinarError(err, 'recordingDelete');
    },
    onSuccess: () => {
      notifySuccess({ title: 'Запись удалена' });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: lessonKey });
    },
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
