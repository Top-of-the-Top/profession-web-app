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

export type CourseContentType = 'published' | 'draft';

export interface AppCourseLesson {
  lesson_id: number | string;
  lesson_number: string;
  title: string;
  slug: string;
  type?: CourseContentType;
}

export interface AppCourseSection {
  section_number: number;
  section_id: number;
  title: string;
  lessons: AppCourseLesson[];
  type?: CourseContentType;
}

export interface AppCourseMeta {
  completed_sections_id: number[];
  completed_lessons_id: number[];
}

export interface AppCourseContentResponse {
  content: AppCourseSection[];
  meta: AppCourseMeta;
}

export interface Lesson {
  lesson_id: number;
  course_id: number;
  title: string;
  slug: string;
  date: string;
  created_at: string;
  updated_at: string;
  last_modified_by: number | null;
}

export interface CourseLessonDetail {
  lesson_id: number | string;
  lesson_title: string;
  content: string;
  recording_url: string | null;
  homework_id: number | string | null;
  homework_deadline: string | null;
  started_at: string | null;
}

export interface PurchasedCourseItem {
  id: number;
  course: CourseDTO;
  payment: number;
  access_expires_at: string | null;
  is_active: boolean;
}

export type AppHomeCoursesSource = 'my-courses' | 'store' | 'landing';

export const APP_HOME_COURSES_SOURCE = 'store' as AppHomeCoursesSource;

type RawCoursesResponse = Course[] | CourseApiAnswer;
type RawCourseBySlugResponse = Course | { course: Course };
type RawAppCourseContentResponse =
  | AppCourseContentResponse
  | { content: AppCourseSection; meta?: Partial<AppCourseMeta> };

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

function normalizeAppCourseContentResponse(
  raw: RawAppCourseContentResponse,
): AppCourseContentResponse {
  const content = Array.isArray(raw.content) ? raw.content : [raw.content];
  const meta = raw.meta ?? {};

  return {
    content,
    meta: {
      completed_sections_id: Array.isArray(meta.completed_sections_id)
        ? meta.completed_sections_id
        : [],
      completed_lessons_id: Array.isArray(meta.completed_lessons_id)
        ? meta.completed_lessons_id
        : [],
    },
  };
}

function catalogRowsToPurchasedShim(rows: CourseDTO[]): PurchasedCourseItem[] {
  return rows.map((course) => ({
    id: course.course_id,
    course,
    payment: 0,
    access_expires_at: null,
    is_active: true,
  }));
}

export const courseApi = {
  getCourses(): Promise<CourseApiAnswer> {
    return apiClient
      .request<RawCoursesResponse>('/api/app/courses/', {
        method: 'GET',
      })
      .then(normalizeCoursesResponse);
  },

  getCourseBySlug(slug: string): Promise<Course> {
    return apiClient
      .request<RawCourseBySlugResponse>(`/api/app/courses/${slug}/`, {
        method: 'GET',
      })
      .then(normalizeCourseBySlugResponse);
  },

  getAppCourseContentBySlug(slug: string): Promise<AppCourseContentResponse> {
    return apiClient
      .request<RawAppCourseContentResponse>(`/api/app/courses/${slug}/`, {
        method: 'GET',
      })
      .then(normalizeAppCourseContentResponse);
  },

  getLessons(courseSlug: string): Promise<Lesson[]> {
    return apiClient.request<Lesson[]>(`/api/courses/${courseSlug}/lessons/`, {
      method: 'GET',
    });
  },

  getLessonBySlug(
    courseSlug: string,
    lessonSlug: string,
  ): Promise<CourseLessonDetail> {
    return apiClient.request<CourseLessonDetail>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
      {
        method: 'GET',
      },
    );
  },

  getMyCourses(): Promise<PurchasedCourseItem[]> {
    return apiClient.request<PurchasedCourseItem[]>('/api/app/my-courses/', {
      method: 'GET',
    });
  },

  async getCoursesForAppHome(): Promise<PurchasedCourseItem[]> {
    if (APP_HOME_COURSES_SOURCE === 'my-courses') {
      return this.getMyCourses();
    }

    const res: CourseApiAnswer =
      APP_HOME_COURSES_SOURCE === 'landing'
        ? await apiClient.request<CourseApiAnswer>('/api/landing/courses/', {
            method: 'GET',
            skipAuth: true,
          })
        : await this.getCourses();

    return catalogRowsToPurchasedShim(res.data ?? []);
  },
};
