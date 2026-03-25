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

/** Урок: GET /api/courses/{course_slug}/lessons/ (поля по LessonSerializer) */
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

/** Детальная информация об уроке: GET /api/courses/{course_slug}/lessons/{slug}/ */
export interface LessonDetail extends Lesson {
  content: Record<string, unknown>;
  has_homework: boolean;
  homework_slug: string | null;
  homework_deadline: string | null;
  board_url: string | null;
  webinar_url: string | null;
}

/** Элемент списка GET /api/app/my-courses/ */
export interface PurchasedCourseItem {
  id: number;
  course: CourseDTO;
  payment: number;
  access_expires_at: string | null;
  is_active: boolean;
}

/**
 * Временный источник списка на `/app/home`.
 * Вернуть `'my-courses'`, когда купленные курсы стабильно отдаются с бэка.
 */
export type AppHomeCoursesSource = 'my-courses' | 'store' | 'landing';

/** Значение по умолчанию — `store`; `as` держит тип объединения (для веток ниже). */
export const APP_HOME_COURSES_SOURCE =
  'store' as AppHomeCoursesSource;

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

  /** Уроки курса (нужна авторизация) */
  getLessons(courseSlug: string): Promise<Lesson[]> {
    return apiClient.request<Lesson[]>(
      `/api/courses/${courseSlug}/lessons/`,
      {
        method: 'GET',
      },
    );
  },

  /** Детальная информация об уроке (нужна авторизация) */
  getLessonBySlug(courseSlug: string, lessonSlug: string): Promise<LessonDetail> {
    return apiClient.request<LessonDetail>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
      {
        method: 'GET',
      },
    );
  },

  /** Купленные курсы текущего пользователя */
  getMyCourses(): Promise<PurchasedCourseItem[]> {
    return apiClient.request<PurchasedCourseItem[]>('/api/app/my-courses/', {
      method: 'GET',
    });
  },

  /**
   * Список для `/app/home` с учётом {@link APP_HOME_COURSES_SOURCE}.
   * Для `store` / `landing` — тот же DTO, что в каталоге; «покупка» подставляется заглушкой.
   */
  async getCoursesForAppHome(): Promise<PurchasedCourseItem[]> {
    if (APP_HOME_COURSES_SOURCE === 'my-courses') {
      return this.getMyCourses();
    }

    const res: CourseApiAnswer =
      APP_HOME_COURSES_SOURCE === 'landing'
        ? await apiClient.request<CourseApiAnswer>('/api/landing/courses/', {
            method: 'GET',
          })
        : await this.getCourses();

    return catalogRowsToPurchasedShim(res.data ?? []);
  },
};