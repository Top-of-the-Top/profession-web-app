import { apiClient } from './interceptor';

export interface WebinarScheduleItem {
  type: 'webinar';
  datetime: string;
  course_title: string;
  course_slug: string;
  title: string;
  webinar_id: string;
  lesson_slug: string;
  webinar_status: 'pending' | 'live' | 'ended';
  scheduled_at: string | null;
}

export interface HomeworkScheduleItem {
  type: 'homework';
  datetime: string;
  course_title: string;
  course_slug: string;
  title: string;
  homework_id: string;
  homework_slug: string;
  homework_lesson_slug: string;
  deadline: string;
  attempt_status: 'not_started' | 'draft' | 'submitted' | 'reviewed' | null;
}

export type ScheduleItem = WebinarScheduleItem | HomeworkScheduleItem;

export interface ScheduleResponse {
  items: ScheduleItem[];
}

export const scheduleApi = {
  getSchedule(params?: { start_date?: string; end_date?: string }): Promise<ScheduleResponse> {
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    const qs = query.toString();
    return apiClient.request<ScheduleResponse>(`/api/v1/my-schedule/${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  },
};
