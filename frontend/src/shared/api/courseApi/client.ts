import { apiClient } from '../interceptor';
import {
  normalizeCourseBySlugResponse,
  normalizeCourseHomeResponse,
  normalizeCoursesResponse,
  normalizeHomeworkAttempt,
  normalizeHomeworkAttemptsList,
  normalizeLessonDetailRead,
  normalizeMyCoursesList,
} from './normalizers';
import type {
  Course,
  CourseApiAnswer,
  CourseDTO,
  CourseItemWriteResponse,
  CourseLessonDetail,
  CoursePatchPayload,
  HomeworkAttempt,
  HomeworkAttemptListItem,
  HomeworkCreatePayload,
  HomeworkDetail,
  HomeworkPatchPayload,
  Lesson,
  LessonCreatePayload,
  LessonPatchPayload,
  MyHomeworksResponse,
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
  ReviewHomeworkAttemptPayload,
  SubmitHomeworkAttemptPayload,
  TaskCreatePayload,
  TaskPatchPayload,
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
    const body: Record<string, unknown> = {
      title: payload.title,
      type: 'draft',
    };
    if (payload.section !== undefined) body.section = payload.section;
    if (payload.document !== undefined) {
      body.content = { document: payload.document };
    }
    return apiClient.request<Lesson>(`/api/courses/${courseSlug}/lessons/`, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  updateLesson(
    courseSlug: string,
    lessonSlug: string,
    payload: LessonPatchPayload,
  ): Promise<Lesson> {
    const body: Record<string, unknown> = {};
    if (payload.title !== undefined) body.title = payload.title;
    if (payload.section !== undefined) body.section = payload.section;
    if (payload.type !== undefined) body.type = payload.type;
    if (payload.date_time !== undefined) body.date_time = payload.date_time;
    if (payload.document !== undefined) {
      body.content = { document: payload.document };
    }
    return apiClient.request<Lesson>(
      `/api/courses/${courseSlug}/lessons/${lessonSlug}/`,
      {
        method: 'PUT',
        body: JSON.stringify(body),
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

  getMyCourses(): Promise<CourseDTO[]> {
    return apiClient
      .request<unknown>('/api/my-courses/', {
        method: 'GET',
      })
      .then(normalizeMyCoursesList);
  },

  getCoursesForAppHome(): Promise<CourseDTO[]> {
    return courseApi.getMyCourses();
  },

  getMyHomeworks(params: {
    courseSlug: string;
    lessonSlug?: string;
  }): Promise<MyHomeworksResponse> {
    const query = new URLSearchParams({ course_slug: params.courseSlug });
    if (params.lessonSlug) query.set('lesson_slug', params.lessonSlug);
    return apiClient.request<MyHomeworksResponse>(
      `/api/my-homeworks/?${query.toString()}`,
      { method: 'GET' },
    );
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

  getHomeworkAttempt(
    courseSlug: string,
    homeworkSlug: string,
  ): Promise<HomeworkAttempt> {
    return apiClient
      .request<RawHomeworkAttempt>(
        `/api/courses/${courseSlug}/homeworks/${homeworkSlug}/attempt/`,
        {
          method: 'GET',
        },
      )
      .then(normalizeHomeworkAttempt);
  },

  submitHomeworkAttempt(
    courseSlug: string,
    homeworkSlug: string,
    payload: SubmitHomeworkAttemptPayload,
  ): Promise<HomeworkAttempt> {
    return apiClient
      .request<RawHomeworkAttempt>(
        `/api/courses/${courseSlug}/homeworks/${homeworkSlug}/attempt/submit/`,
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
      )
      .then(normalizeHomeworkAttempt);
  },

  getHomeworkAttemptsByCourse(courseSlug: string): Promise<HomeworkAttemptListItem[]> {
    return apiClient
      .request<unknown>(`/api/courses/${courseSlug}/attempts/`, {
        method: 'GET',
      })
      .then(normalizeHomeworkAttemptsList);
  },

  getHomeworkAttemptForReview(
    courseSlug: string,
    attemptId: string,
  ): Promise<HomeworkAttempt> {
    return apiClient
      .request<RawHomeworkAttempt>(`/api/courses/${courseSlug}/attempts/${attemptId}/`, {
        method: 'GET',
      })
      .then(normalizeHomeworkAttempt);
  },

  reviewHomeworkAttempt(
    courseSlug: string,
    attemptId: string,
    payload: ReviewHomeworkAttemptPayload,
  ): Promise<HomeworkAttempt> {
    return apiClient
      .request<RawHomeworkAttempt>(
        `/api/courses/${courseSlug}/attempts/${attemptId}/review/`,
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
      )
      .then(normalizeHomeworkAttempt);
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
