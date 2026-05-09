import { apiClient } from './interceptor';

export interface ScheduleItem {
  type: 'webinar' | 'homework';
  datetime: string;
  course_title: string;
  title: string;
}

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
