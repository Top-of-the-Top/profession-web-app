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

export interface Course extends CourseDTO {
  created_at: string;
  updated_at: string;
  description: string;
  image: string;
  last_modified_by: number;
  authors: number[];
}

export interface CourseApiAnswer {
  number_of_courses: number;
  data: CourseDTO[];
}

type RawCoursesResponse = Course[] | CourseApiAnswer;
type RawCourseBySlugResponse = Course | { course: Course };

function normalizeCoursesResponse(raw: RawCoursesResponse): CourseApiAnswer {
  if (Array.isArray(raw)) {
    return {
      number_of_courses: raw.length,
      data: raw,
    };
  }

  return {
    number_of_courses: Number(raw.number_of_courses ?? 0),
    data: Array.isArray(raw.data) ? raw.data : [],
  };
}

function normalizeCourseBySlugResponse(raw: RawCourseBySlugResponse): Course {
  if ('course' in raw) {
    return raw.course;
  }

  return raw;
}

export const courseApi = {
  /**
   * Получить список всех курсов
   */
  getCourses(): Promise<CourseApiAnswer> {
    return apiClient
      .request<RawCoursesResponse>('/api/app/courses/', {
      method: 'GET',
      })
      .then(normalizeCoursesResponse);
  },

  /**
   * Получить курс по slug
   */
  getCourseBySlug(slug: string): Promise<Course> {
    return apiClient
      .request<RawCourseBySlugResponse>(`/api/app/courses/${slug}/`, {
        method: 'GET',
      })
      .then(normalizeCourseBySlugResponse);
  },
};