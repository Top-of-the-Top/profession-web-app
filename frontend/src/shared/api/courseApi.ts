// shared/api/courseApi.ts
import { apiClient } from './interceptor';

export interface CourseDTO {
  course_id: number;
  title: string;
  sub_title: string;
  image_url: string;
  price: number;
  slug: string;
}
export interface Course extends CourseDTO{
	created_at: string,
	description: string
}

export interface CourseApiAnswer {
	number_of_courses: string,
	data: CourseDTO[]
}
// TODO: ЭТО КОСТЫЛЬ! ПОГОВОРИТЬ С СЕМЕНОМ
export interface CourseBySlugAnswer {
	course: Course;
}

export const courseApi = {
  /**
   * Получить список всех курсов
   */
  getCourses(): Promise<CourseApiAnswer> {
    return apiClient.request<CourseApiAnswer>('/api/app/store/', {
      method: 'GET',
    });
  },

  /**
   * Получить курс по slug
   */
  getCourseBySlug(slug: string): Promise<CourseBySlugAnswer> {
    return apiClient.request<CourseBySlugAnswer>(`/api/app/courses/${slug}/`, {
      method: 'GET',
    });
  },
};