import { apiClient } from '../../../shared/api/interceptor';
import type { LessonLayoutDTO } from '../model/types';

export interface SaveLessonLayoutParams {
  courseId: number;
  layout: LessonLayoutDTO;
}

export const courseBuilderApi = {
  async load(courseId: number): Promise<LessonLayoutDTO> {
    return apiClient.request<LessonLayoutDTO>(
      `/api/app/courses/${courseId}/structure/`,
      { method: 'GET' },
    );
  },

  async save({ courseId, layout }: SaveLessonLayoutParams): Promise<void> {
    await apiClient.request(`/api/app/courses/${courseId}/structure/`, {
      method: 'PUT',
      body: JSON.stringify(layout),
    });
  },
};

