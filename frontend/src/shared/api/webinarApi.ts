import { apiClient } from './interceptor';

export interface WebinarJoinResponse {
  rtc_token: string;
  agora_app_id: string;
  channel_name: string;
  uid: number;
  whiteboard_app_id: string;
  whiteboard_room_uuid: string;
  whiteboard_room_token: string;
  whiteboard_region: string;
  role: 'teacher' | 'student';
}

export interface WebinarStartResponse {
  detail: string;
  webinar_id: string;
}

export interface WebinarDetailResponse {
  detail: string;
}

function webinarBase(courseSlug: string, lessonSlug: string) {
  return `/api/courses/${courseSlug}/lessons/${lessonSlug}/webinar`;
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

  startRecording(courseSlug: string, lessonSlug: string): Promise<WebinarDetailResponse> {
    return apiClient.request<WebinarDetailResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/recording/start/`,
      { method: 'POST' },
    );
  },

  stop(courseSlug: string, lessonSlug: string): Promise<WebinarDetailResponse> {
    return apiClient.request<WebinarDetailResponse>(
      `${webinarBase(courseSlug, lessonSlug)}/stop/`,
      { method: 'POST' },
    );
  },
};
