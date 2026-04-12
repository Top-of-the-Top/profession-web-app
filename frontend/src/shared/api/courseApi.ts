import { apiClient } from './interceptor';

export interface CourseDTO {
  course_id: string;
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
  last_modified_by: number | null;
  authors: number[];
}

export interface CourseApiAnswer {
  number_of_courses: number;
  data: CourseDTO[];
}

export type CourseContentType = 'published' | 'draft';

export interface AppCourseLesson {
  lesson_id: string;
  lesson_number: number;
  title: string;
  slug: string;
  type?: CourseContentType;
}

export interface AppCourseSection {
  section_id: string;
  section_number: number;
  title: string;
  slug?: string;
  lessons: AppCourseLesson[];
  type?: CourseContentType;
}

export interface CourseHomeMeta {
  completed_sections_id: string[];
  completed_lessons_id: string[];
}

export interface CourseHomeResponse {
  course_id: string;
  title: string;
  content: AppCourseSection[];
  meta: CourseHomeMeta;
}

export type AppCourseContentResponse = CourseHomeResponse;

export interface Lesson {
  lesson_id: string;
  section?: string | null;
  lesson_number: number;
  title: string;
  slug: string;
  type?: CourseContentType;
  date_time?: string | null;
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
  id: string | number;
  course: CourseDTO;
  payment: number;
  access_expires_at: string | null;
  is_active: boolean;
}

export interface SectionCreatePayload {
  title: string;
}

export interface SectionPatchPayload {
  title?: string;
  type?: CourseContentType;
}

export interface SectionRecord {
  section_id: string;
  section_number: number;
  title: string;
  slug: string;
  course: string;
  type: CourseContentType;
  created_at: string;
  updated_at: string;
  last_modified_by: number | null;
}

export interface LessonCreatePayload {
  title: string;
  section?: string;
  date_time?: string | null;
}

export interface LessonPatchPayload {
  title?: string;
  section?: string | null;
  type?: CourseContentType;
  date_time?: string | null;
}

export interface CoursePatchPayload {
  title?: string;
  sub_title?: string;
  description?: string;
  price?: number;
  type?: CourseContentType;
}

export type AppHomeCoursesSource = 'my-courses' | 'store' | 'landing';

export const APP_HOME_COURSES_SOURCE = 'store' as AppHomeCoursesSource;

type RawCoursesResponse = Course[] | CourseApiAnswer;
type RawCourseBySlugResponse = Course | { course: Course };
type RawCourseHomeResponse = Partial<CourseHomeResponse> & {
  content?: AppCourseSection | AppCourseSection[];
  meta?: Record<string, unknown>;
};

type RawLessonDetailContent = {
  recording_url?: string;
  started_at?: string | null;
  homeworks?: Array<{
    homework_id: string;
    title: string;
    homework_slug: string;
    deadline: string;
  }>;
};

type RawLessonDetailResponse = {
  lesson_id: string;
  title: string;
  content: RawLessonDetailContent | string;
};

function normalizeCoursesResponse(raw: RawCoursesResponse): CourseApiAnswer {
  if (Array.isArray(raw)) {
    return {
      number_of_courses: raw.length,
      data: raw.map((c) => ({
        ...c,
        course_id: String(c.course_id),
      })),
    };
  }

  return {
    number_of_courses: Number(raw.number_of_courses ?? 0),
    data: Array.isArray(raw.data)
      ? raw.data.map((c) => ({
          ...c,
          course_id: String(c.course_id),
        }))
      : [],
  };
}

function normalizeCourseBySlugResponse(raw: RawCourseBySlugResponse): Course {
  const c = 'course' in raw ? raw.course : raw;
  return {
    ...c,
    course_id: String(c.course_id),
    last_modified_by: c.last_modified_by ?? null,
  };
}

function normalizeIdList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item));
}

function normalizeCourseHomeResponse(raw: RawCourseHomeResponse): CourseHomeResponse {
  const rawContent = raw.content;
  const content: AppCourseSection[] = Array.isArray(rawContent)
    ? rawContent
    : rawContent != null
      ? [rawContent as AppCourseSection]
      : [];

  const metaObj =
    raw.meta != null && typeof raw.meta === 'object' && !Array.isArray(raw.meta)
      ? (raw.meta as Record<string, unknown>)
      : {};

  return {
    course_id: String(raw.course_id ?? ''),
    title: String(raw.title ?? ''),
    content,
    meta: {
      completed_sections_id: normalizeIdList(metaObj.completed_sections_id),
      completed_lessons_id: normalizeIdList(metaObj.completed_lessons_id),
    },
  };
}

function normalizeLessonDetailRead(raw: RawLessonDetailResponse): CourseLessonDetail {
  const contentVal = raw.content;
  const nest =
    typeof contentVal === 'object' && contentVal !== null && !Array.isArray(contentVal)
      ? (contentVal as RawLessonDetailContent)
      : null;
  const builderContent =
    typeof contentVal === 'string'
      ? contentVal
      : JSON.stringify({
          id: String(raw.lesson_id),
          title: raw.title,
          blocks: [],
        });
  const firstHw = nest?.homeworks?.[0];
  return {
    lesson_id: raw.lesson_id,
    lesson_title: raw.title,
    content: builderContent,
    recording_url: nest?.recording_url ?? null,
    homework_id: firstHw?.homework_id ?? null,
    homework_deadline: firstHw?.deadline ?? null,
    started_at: nest?.started_at ?? null,
  };
}

function catalogRowsToPurchasedShim(rows: CourseDTO[]): PurchasedCourseItem[] {
  return rows.map((course) => ({
    id: String(course.course_id),
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

  getCourseHomeBySlug(slug: string): Promise<CourseHomeResponse> {
    return apiClient
      .request<RawCourseHomeResponse>(`/api/app/courses/${slug}/home/`, {
        method: 'GET',
      })
      .then(normalizeCourseHomeResponse);
  },

  patchCourse(slug: string, payload: CoursePatchPayload): Promise<Course> {
    return apiClient
      .request<RawCourseBySlugResponse>(`/api/app/courses/${slug}/`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      .then(normalizeCourseBySlugResponse);
  },

  createSection(
    courseSlug: string,
    payload: SectionCreatePayload,
  ): Promise<SectionRecord> {
    return apiClient.request<SectionRecord>(
      `/api/courses/${courseSlug}/sections/`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
  },

  patchSection(
    courseSlug: string,
    sectionSlug: string,
    payload: SectionPatchPayload,
  ): Promise<SectionRecord> {
    return apiClient.request<SectionRecord>(
      `/api/courses/${courseSlug}/sections/${sectionSlug}/`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
    );
  },

  deleteSection(courseSlug: string, sectionSlug: string): Promise<void> {
    return apiClient.request<void>(
      `/api/courses/${courseSlug}/sections/${sectionSlug}/`,
      { method: 'DELETE' },
    );
  },

  createLesson(courseSlug: string, payload: LessonCreatePayload): Promise<Lesson> {
    return apiClient.request<Lesson>(`/api/courses/${courseSlug}/lessons/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  patchLesson(
    courseSlug: string,
    lessonSlug: string,
    payload: LessonPatchPayload,
  ): Promise<Lesson> {
    return apiClient.request<Lesson>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      },
    );
  },

  deleteLesson(courseSlug: string, lessonSlug: string): Promise<void> {
    return apiClient.request<void>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
      { method: 'DELETE' },
    );
  },

  getLessonBySlug(
    courseSlug: string,
    lessonSlug: string,
  ): Promise<CourseLessonDetail> {
    return apiClient
      .request<RawLessonDetailResponse>(
        `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
        {
          method: 'GET',
        },
      )
      .then(normalizeLessonDetailRead);
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
        ? await apiClient
            .request<CourseApiAnswer>('/api/landing/courses/', {
              method: 'GET',
              skipAuth: true,
            })
            .then((raw) => normalizeCoursesResponse(raw as RawCoursesResponse))
        : await this.getCourses();

    return catalogRowsToPurchasedShim(res.data ?? []);
  },
};
