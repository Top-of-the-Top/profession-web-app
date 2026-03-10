import { apiClient } from '../../../shared/api/interceptor';
import type { CourseStructureDTO } from '../model/types';

export interface SaveCourseStructureParams {
  courseId: number;
  structure: CourseStructureDTO;
}

export const courseBuilderApi = {
  async load(courseId: number): Promise<CourseStructureDTO> {
    return apiClient.request<CourseStructureDTO>(`/api/app/courses/${courseId}/structure/`, {
      method: 'GET',
    });
  },

  async save({ courseId, structure }: SaveCourseStructureParams): Promise<void> {
    await apiClient.request(`/api/app/courses/${courseId}/structure/`, {
      method: 'PUT',
      body: JSON.stringify(structure),
    });
  },
};

