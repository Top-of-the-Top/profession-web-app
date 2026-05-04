import { apiClient } from '../interceptor';
import {
  buildLessonFormData,
  normalizeCourseBySlugResponse,
  normalizeCourseHomeResponse,
  normalizeCoursesResponse,
  normalizeHomeworkAttempt,
  normalizeLessonDetailRead,
} from './normalizers';
import type {
  Course,
  CourseApiAnswer,
  CourseItemWriteResponse,
  CourseLessonDetail,
  CoursePatchPayload,
  HomeworkAttempt,
  HomeworkCreatePayload,
  HomeworkDetail,
  HomeworkPatchPayload,
  HomeworkUploadResponse,
  Lesson,
  LessonCreatePayload,
  LessonPatchPayload,
  PurchasedCourseItem,
  QuestionCreatePayload,
  QuestionPatchPayload,
  RawCourseBySlugResponse,
  RawCourseHomeResponse,
  RawCoursesResponse,
  RawHomeworkAttempt,
  RawLessonDetailResponse,
  SectionCreatePayload,
  SectionPatchPayload,
  SectionRecord,
  SubmitHomeworkAttemptPayload,
  TaskCreatePayload,
  TaskPatchPayload,
  UploadHomeworkFilePayload,
} from './types';

export const courseApi = {
  getCourses(): Promise<CourseApiAnswer> {
    return apiClient
      .request<RawCoursesResponse>('/api/courses/', {
        method: 'GET',
      })
      .then(normalizeCoursesResponse);
  },

  getCourseBySlug(slug: string): Promise<Course> {
    return apiClient
      .request<RawCourseBySlugResponse>(`/api/courses/${slug}/`, {
        method: 'GET',
      })
      .then(normalizeCourseBySlugResponse);
  },

  getCourseHomeBySlug(slug: string) {
    return apiClient
      .request<RawCourseHomeResponse>(`/api/courses/${slug}/home/`, {
        method: 'GET',
      })
      .then(normalizeCourseHomeResponse);
  },

  patchCourse(slug: string, payload: CoursePatchPayload): Promise<Course> {
    return apiClient
      .request<RawCourseBySlugResponse>(`/api/courses/${slug}/`, {
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
    const hasFiles = payload.files && Object.keys(payload.files).length > 0;
    const hasDocument =
      payload.document != null && String(payload.document).trim() !== '';

    if (hasFiles || hasDocument) {
      const body = hasFiles
        ? buildLessonFormData(payload)
        : JSON.stringify({
            title: payload.title,
            section: payload.section,
            type: 'draft',
            content: { document: payload.document ?? '', assets: [] },
          });

      return apiClient.request<Lesson>(`/api/courses/${courseSlug}/lessons/`, {
        method: 'PUT',
        body,
      });
    }

    return apiClient.request<Lesson>(`/api/courses/${courseSlug}/lessons/`, {
      method: 'POST',
      body: JSON.stringify({
        title: payload.title,
        section: payload.section,
        type: 'draft',
      }),
    });
  },

  updateLesson(
    courseSlug: string,
    lessonSlug: string,
    payload: LessonPatchPayload,
  ): Promise<Lesson> {
    const hasFiles = payload.files && Object.keys(payload.files).length > 0;
    const hasDocument = payload.document != null;

    let body: FormData | string;
    if (hasFiles || hasDocument) {
      body = buildLessonFormData(payload);
    } else {
      const meta: Record<string, unknown> = { ...payload };
      delete meta.files;
      delete meta.document;
      body = JSON.stringify(meta);
    }

    return apiClient.request<Lesson>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
      {
        method: 'PUT',
        body,
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
    return apiClient.request<PurchasedCourseItem[]>('/api/my-courses/', {
      method: 'GET',
    });
  },

  getCoursesForAppHome(): Promise<PurchasedCourseItem[]> {
    return courseApi.getMyCourses();
  },

  createHomework(
    courseSlug: string,
    lessonSlug: string,
    payload: HomeworkCreatePayload,
  ): Promise<HomeworkDetail> {
    return apiClient.request<HomeworkDetail>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  getHomeworkDetail(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
  ): Promise<HomeworkDetail> {
    return apiClient.request<HomeworkDetail>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/`,
      { method: 'GET' },
    );
  },

  getHomeworkAttempt(homeworkSlug: string): Promise<HomeworkAttempt> {
    return apiClient
      .request<RawHomeworkAttempt>(`/api/homeworks/${homeworkSlug}/attempt/`, {
        method: 'GET',
      })
      .then(normalizeHomeworkAttempt);
  },

  submitHomeworkAttempt(
    homeworkSlug: string,
    payload: SubmitHomeworkAttemptPayload,
  ): Promise<HomeworkAttempt> {
    return apiClient
      .request<RawHomeworkAttempt>(`/api/homeworks/${homeworkSlug}/attempt/submit`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      .then(normalizeHomeworkAttempt);
  },

  requestHomeworkUpload(
    homeworkSlug: string,
    payload: UploadHomeworkFilePayload,
  ): Promise<HomeworkUploadResponse> {
    return apiClient.request<HomeworkUploadResponse>(
      `/api/homeworks/${homeworkSlug}/attempt/upload_file`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
  },

  patchHomework(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    payload: HomeworkPatchPayload,
  ): Promise<HomeworkDetail> {
    return apiClient.request<HomeworkDetail>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/`,
      { method: 'PATCH', body: JSON.stringify(payload) },
    );
  },

  deleteHomework(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
  ): Promise<void> {
    return apiClient.request<void>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/`,
      { method: 'DELETE' },
    );
  },

  createQuestion(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    payload: QuestionCreatePayload,
  ): Promise<CourseItemWriteResponse> {
    return apiClient.request<CourseItemWriteResponse>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/questions/`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  patchQuestion(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    questionId: string,
    payload: QuestionPatchPayload,
  ): Promise<CourseItemWriteResponse> {
    return apiClient.request<CourseItemWriteResponse>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/questions/${questionId}/`,
      { method: 'PATCH', body: JSON.stringify(payload) },
    );
  },

  deleteQuestion(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    questionId: string,
  ): Promise<void> {
    return apiClient.request<void>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/questions/${questionId}/`,
      { method: 'DELETE' },
    );
  },

  createTask(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    payload: TaskCreatePayload,
  ): Promise<CourseItemWriteResponse> {
    return apiClient.request<CourseItemWriteResponse>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/tasks/`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  patchTask(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    taskId: string,
    payload: TaskPatchPayload,
  ): Promise<CourseItemWriteResponse> {
    return apiClient.request<CourseItemWriteResponse>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/tasks/${taskId}/`,
      { method: 'PATCH', body: JSON.stringify(payload) },
    );
  },

  deleteTask(
    courseSlug: string,
    lessonSlug: string,
    homeworkSlug: string,
    taskId: string,
  ): Promise<void> {
    return apiClient.request<void>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/homeworks/${homeworkSlug}/tasks/${taskId}/`,
      { method: 'DELETE' },
    );
  },
};
