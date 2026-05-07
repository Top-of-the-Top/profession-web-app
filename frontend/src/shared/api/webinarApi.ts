import { apiClient } from './interceptor';

export type WebinarRole = 'teacher' | 'student' | 'moderator' | 'recorder';

export interface WebinarJoinResponse {
  rtc_token: string;
  agora_app_id: string;
  channel_name: string;
  uid: number;
  user_name: string;
  whiteboard_app_id: string;
  whiteboard_room_uuid: string;
  whiteboard_room_token: string;
  whiteboard_region: string;
  role: WebinarRole;
  rtm_token: string;
  chat_channel_name: string;
  webinar_id?: string;
}

export interface WebinarStartResponse {
  detail: string;
  webinar_id: string;
}

export interface WebinarDetailResponse {
  detail: string;
}

export interface WebinarRecordingResponse extends WebinarDetailResponse {
  recording_id: string;
}

export interface WebinarFinalPdfResponse extends WebinarRecordingResponse {
  whiteboard_pdf_url: string;
}

function webinarBase(courseSlug: string, lessonSlug: string) {
  return `/api/courses/${courseSlug}/lessons/${lessonSlug}/webinar`;
}

function lessonBase(courseSlug: string, lessonSlug: string) {
  return `/api/courses/${courseSlug}/lessons/${lessonSlug}`;
}

export const webinarApi = {
  start(courseSlug: string, lessonSlug: string): Promise<WebinarStartResponse> {
    return apiClient.request<WebinarStartResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/start/`,
      { method: 'POST' },
    );
  },

  join(courseSlug: string, lessonSlug: string): Promise<WebinarJoinResponse> {
    return apiClient.request<WebinarJoinResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/join/`,
      { method: 'GET' },
    );
  },

  startRecording(
    courseSlug: string,
    lessonSlug: string,
  ): Promise<WebinarRecordingResponse> {
    return apiClient.request<WebinarRecordingResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/recording/start/`,
      { method: 'POST' },
    );
  },

  stopRecording(
    courseSlug: string,
    lessonSlug: string,
  ): Promise<WebinarRecordingResponse> {
    return apiClient.request<WebinarRecordingResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/recording/stop/`,
      { method: 'POST' },
    );
  },

  uploadRecordingPdf(
    courseSlug: string,
    lessonSlug: string,
    recordingId: string,
    screenshots: Blob[],
  ): Promise<WebinarDetailResponse> {
    const fd = new FormData();
    screenshots.forEach((blob, index) => {
      const name = `scene-${index + 1}.png`;
      fd.append('screenshots', blob, name);
    });

    return apiClient.request<WebinarDetailResponse>(
      `${lessonBase(courseSlug, lessonSlug)}/recordings/${recordingId}/pdf/`,
      { method: 'POST', body: fd },
    );
  },

  uploadFinalPdf(
    courseSlug: string,
    lessonSlug: string,
    screenshots: Blob[],
  ): Promise<WebinarFinalPdfResponse> {
    const fd = new FormData();
    screenshots.forEach((blob, index) => {
      const name = `scene-${index + 1}.png`;
      fd.append('screenshots', blob, name);
    });

    return apiClient.request<WebinarFinalPdfResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/final-pdf/`,
      { method: 'POST', body: fd },
    );
  },

  deleteRecordingPdf(
    courseSlug: string,
    lessonSlug: string,
    recordingId: string,
  ): Promise<void> {
    return apiClient.request<void>(
      `${lessonBase(courseSlug, lessonSlug)}/recordings/${recordingId}/pdf/`,
      { method: 'DELETE' },
    );
  },

  deleteRecording(
    courseSlug: string,
    lessonSlug: string,
    recordingId: string,
  ): Promise<void> {
    return apiClient.request<void>(
      `${lessonBase(courseSlug, lessonSlug)}/recordings/${recordingId}/`,
      { method: 'DELETE' },
    );
  },

  stop(courseSlug: string, lessonSlug: string): Promise<WebinarDetailResponse> {
    return apiClient.request<WebinarDetailResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/stop/`,
      { method: 'POST' },
    );
  },

  recorderJoin(
    courseSlug: string,
    lessonSlug: string,
    token: string,
  ): Promise<WebinarJoinResponse> {
    const qs = `?token=${encodeURIComponent(token)}`;
    return apiClient.request<WebinarJoinResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/recorder-join/${qs}`,
      { method: 'GET', skipAuth: true },
    );
  },
};
