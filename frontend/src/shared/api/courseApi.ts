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

export interface LessonHomework {
  homework_id: string;
  title: string;
  deadline: string;
  homework_slug: string;
  type: CourseContentType;
}

export interface HomeworkDetailItem {
  type: 'question' | 'task';
  id: string;
  number: number;
  text: string;
  answer_options?: string[] | null;
  correct_ans?: string | null;
  max_points?: number | null;
  created_at: string;
}

export interface HomeworkDetail {
  homework_id: string;
  homework_number: number;
  lesson_id: string;
  title: string;
  slug: string;
  deadline: string;
  type: CourseContentType;
  created_at: string;
  updated_at: string;
  items: HomeworkDetailItem[];
}

export type HomeworkAttemptStatus = 'draft' | 'submitted' | 'reviewed';

export interface HomeworkAttemptAttachment {
  attachment_id: string;
  file_name: string;
  file_url: string;
  file_size: number;
  file_extension: string;
}

export interface HomeworkAttemptQuestionItem {
  type: 'question';
  question_id: string;
  answer_id: string;
  status: string;
  number: number;
  text: string;
  answer_options: string[];
  user_answer: string | null;
  max_points: number;
}

export interface HomeworkAttemptTaskItem {
  type: 'task';
  task_id: string;
  answer_id: string;
  status: string;
  number: number;
  text: string;
  user_answer: string | null;
  points: number | null;
  max_points: number;
  teacher_comment: string | null;
  file_attachments: HomeworkAttemptAttachment[];
}

export type HomeworkAttemptItem = HomeworkAttemptQuestionItem | HomeworkAttemptTaskItem;

export interface HomeworkAttempt {
  homework_id: string;
  attempt_id: string;
  status: HomeworkAttemptStatus;
  deadline: string;
  score: number | null;
  max_points: number | null;
  items: HomeworkAttemptItem[];
}

export interface SubmitHomeworkAttemptItemQuestionPayload {
  type: 'question';
  id: string;
  number: number;
  user_answer: string | null;
}

export interface SubmitHomeworkAttemptItemTaskPayload {
  type: 'task';
  id: string;
  number: number;
  user_answer: string | null;
  file_attachments?: HomeworkAttemptAttachment[];
}

export type SubmitHomeworkAttemptItemPayload =
  | SubmitHomeworkAttemptItemQuestionPayload
  | SubmitHomeworkAttemptItemTaskPayload;

export interface SubmitHomeworkAttemptPayload {
  homework_id: string;
  attempt_id: string;
  send_at: string;
  items: SubmitHomeworkAttemptItemPayload[];
}

export interface UploadHomeworkFilePayload {
  attempt_id: string;
  task_id: string;
  file_name: string;
  file_size: number;
  file_extension: string;
}

export interface HomeworkUploadResponse {
  url: string;
  method: string;
  expires_at: string;
  fields: Record<string, string>;
}

export interface HomeworkCreatePayload {
  title: string;
  deadline: string;
  type?: CourseContentType;
}

export interface HomeworkPatchPayload {
  title?: string;
  deadline?: string;
  type?: CourseContentType;
}

export interface QuestionCreatePayload {
  text: string;
  correct_ans?: string | null;
  answer_options?: string[] | null;
}

export interface QuestionPatchPayload {
  text?: string;
  correct_ans?: string | null;
  answer_options?: string[] | null;
}

export interface TaskCreatePayload {
  text: string;
  max_points?: number;
}

export interface TaskPatchPayload {
  text?: string;
  max_points?: number;
}

export type WebinarStatus = 'pending' | 'live' | 'ended';

export type KinescopeUploadStatus =
  | 'none'
  | 'pending'
  | 'uploading'
  | 'processing'
  | 'ready'
  | 'failed';

export type RecordingStatus = 'recording' | 'processing' | 'ready' | 'failed';

export interface LessonRecording {
  recording_id: string;
  started_at: string | null;
  ended_at: string | null;
  status: RecordingStatus;
  kinescope_upload_status: KinescopeUploadStatus;
  kinescope_embed_url: string;
  whiteboard_pdf_url: string;
}

export interface CourseLessonDetail {
  lesson_id: number;
  title: string;
  document: string;
  started_at: string | null;
  webinar_status: WebinarStatus | null;
  recordings: LessonRecording[];
  homeworks: LessonHomework[];
  meta: Record<string, unknown>;
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
  lesson_num?: number;
  document?: string;
  files?: Record<string, File>;
}

export interface LessonPatchPayload {
  title?: string;
  section?: string | null;
  type?: CourseContentType;
  date_time?: string | null;
  document?: string;
  files?: Record<string, File>;
}

export interface CoursePatchPayload {
  title?: string;
  sub_title?: string;
  description?: string;
  price?: number;
  type?: CourseContentType;
}

type RawCoursesResponse = Course[] | CourseApiAnswer;
type RawCourseBySlugResponse = Course | { course: Course };
type RawCourseHomeResponse = Partial<CourseHomeResponse> & {
  content?: AppCourseSection | AppCourseSection[];
  meta?: Record<string, unknown>;
};

type RawLessonDetailResponse = {
  lesson_id: number;
  title: string;
  content: {
    document?: string;
    recording_url?: string | null;
    started_at?: string | null;
    webinar_status?: WebinarStatus | null;
    whiteboard_pdf_url?: string | null;
    kinescope_embed_url?: string | null;
    kinescope_upload_status?: KinescopeUploadStatus | null;
    recordings?: Array<{
      recording_id?: string;
      started_at?: string | null;
      ended_at?: string | null;
      status?: RecordingStatus;
      kinescope_upload_status?: KinescopeUploadStatus | null;
      kinescope_embed_url?: string | null;
      whiteboard_pdf_url?: string | null;
    }>;
    homeworks?: LessonHomework[];
  };
  meta?: Record<string, unknown>;
};

type RawHomeworkAttemptAttachment = {
  attachment_id?: unknown;
  file_name?: unknown;
  file_url?: unknown;
  file_size?: unknown;
  file_extension?: unknown;
  file_format?: unknown;
};

type RawHomeworkAttemptQuestionItem = {
  type: 'question';
  question_id?: unknown;
  answer_id?: unknown;
  status?: unknown;
  number?: unknown;
  text?: unknown;
  answer_options?: unknown;
  user_answer?: unknown;
  max_points?: unknown;
};

type RawHomeworkAttemptTaskItem = {
  type: 'task';
  task_id?: unknown;
  answer_id?: unknown;
  status?: unknown;
  number?: unknown;
  text?: unknown;
  user_answer?: unknown;
  points?: unknown;
  max_points?: unknown;
  teacher_comment?: unknown;
  file_attachments?: unknown;
};

type RawHomeworkAttempt = {
  homework_id?: unknown;
  attempt_id?: unknown;
  status?: unknown;
  deadline?: unknown;
  score?: unknown;
  max_points?: unknown;
  items?: unknown;
};

function normalizeLessonRecordings(
  content: RawLessonDetailResponse['content'],
): LessonRecording[] {
  const list = Array.isArray(content.recordings) ? content.recordings : [];
  if (list.length > 0) {
    return list.map((recording) => ({
      recording_id: String(recording.recording_id ?? ''),
      started_at: recording.started_at ?? null,
      ended_at: recording.ended_at ?? null,
      status: recording.status ?? 'processing',
      kinescope_upload_status: recording.kinescope_upload_status ?? 'none',
      kinescope_embed_url: recording.kinescope_embed_url ?? '',
      whiteboard_pdf_url: recording.whiteboard_pdf_url ?? '',
    }));
  }

  if (
    !content.recording_url &&
    !content.kinescope_embed_url &&
    !content.whiteboard_pdf_url &&
    (content.kinescope_upload_status == null || content.kinescope_upload_status === 'none')
  ) {
    return [];
  }

  const fallbackStatus: RecordingStatus =
    content.kinescope_upload_status === 'failed'
      ? 'failed'
      : content.kinescope_upload_status === 'ready'
        ? 'ready'
        : 'processing';

  return [
    {
      recording_id: '',
      started_at: content.started_at ?? null,
      ended_at: null,
      status: fallbackStatus,
      kinescope_upload_status: content.kinescope_upload_status ?? 'none',
      kinescope_embed_url: content.kinescope_embed_url ?? '',
      whiteboard_pdf_url: content.whiteboard_pdf_url ?? '',
    },
  ];
}

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
  const c = raw.content ?? {};
  return {
    lesson_id: raw.lesson_id,
    title: raw.title,
    document: c.document ?? '',
    started_at: c.started_at ?? null,
    webinar_status: c.webinar_status ?? null,
    recordings: normalizeLessonRecordings(c),
    homeworks: Array.isArray(c.homeworks) ? c.homeworks : [],
    meta: raw.meta ?? {},
  };
}

function normalizeAttemptAttachment(
  attachment: RawHomeworkAttemptAttachment,
): HomeworkAttemptAttachment {
  const extensionRaw = attachment.file_extension ?? attachment.file_format;
  return {
    attachment_id: String(attachment.attachment_id ?? ''),
    file_name: String(attachment.file_name ?? ''),
    file_url: String(attachment.file_url ?? ''),
    file_size: Number(attachment.file_size ?? 0),
    file_extension: String(extensionRaw ?? ''),
  };
}

function normalizeHomeworkAttemptItem(item: unknown): HomeworkAttemptItem | null {
  if (!item || typeof item !== 'object') {
    return null;
  }

  if ((item as { type?: unknown }).type === 'question') {
    const question = item as RawHomeworkAttemptQuestionItem;
    return {
      type: 'question',
      question_id: String(question.question_id ?? ''),
      answer_id: String(question.answer_id ?? ''),
      status: String(question.status ?? ''),
      number: Number(question.number ?? 0),
      text: String(question.text ?? ''),
      answer_options: Array.isArray(question.answer_options)
        ? question.answer_options.map((option) => String(option))
        : [],
      user_answer:
        question.user_answer == null ? null : String(question.user_answer),
      max_points: Number(question.max_points ?? 0),
    };
  }

  if ((item as { type?: unknown }).type === 'task') {
    const task = item as RawHomeworkAttemptTaskItem;
    return {
      type: 'task',
      task_id: String(task.task_id ?? ''),
      answer_id: String(task.answer_id ?? ''),
      status: String(task.status ?? ''),
      number: Number(task.number ?? 0),
      text: String(task.text ?? ''),
      user_answer: task.user_answer == null ? null : String(task.user_answer),
      points: task.points == null ? null : Number(task.points),
      max_points: Number(task.max_points ?? 0),
      teacher_comment:
        task.teacher_comment == null ? null : String(task.teacher_comment),
      file_attachments: Array.isArray(task.file_attachments)
        ? task.file_attachments.map((attachment) =>
            normalizeAttemptAttachment(
              attachment as RawHomeworkAttemptAttachment,
            ),
          )
        : [],
    };
  }

  return null;
}

function normalizeHomeworkAttempt(raw: RawHomeworkAttempt): HomeworkAttempt {
  const normalizedStatus = String(raw.status ?? 'draft');
  const itemsRaw = Array.isArray(raw.items) ? raw.items : [];
  return {
    homework_id: String(raw.homework_id ?? ''),
    attempt_id: String(raw.attempt_id ?? ''),
    status:
      normalizedStatus === 'submitted' || normalizedStatus === 'reviewed'
        ? normalizedStatus
        : 'draft',
    deadline: String(raw.deadline ?? ''),
    score: raw.score == null ? null : Number(raw.score),
    max_points: raw.max_points == null ? null : Number(raw.max_points),
    items: itemsRaw
      .map((item) => normalizeHomeworkAttemptItem(item))
      .filter((item): item is HomeworkAttemptItem => item != null),
  };
}

const ASSET_PART_PREFIX = 'asset_' as const;

function guessAssetType(file: File): string {
  if (file.type.startsWith('video/')) return 'video';
  return 'image';
}

function buildLessonFormData(
  payload: LessonCreatePayload | LessonPatchPayload,
): FormData {
  const fd = new FormData();

  if (payload.title != null) fd.set('title', payload.title);
  if ('section' in payload && payload.section != null)
    fd.set('section', payload.section);
  if ('lesson_num' in payload && (payload as LessonCreatePayload).lesson_num != null)
    fd.set('lesson_num', String((payload as LessonCreatePayload).lesson_num));

  const files = payload.files;
  const assetIds = files ? Object.keys(files) : [];
  const assets = assetIds.map((id) => ({
    asset_id: Number(id),
    asset_type: guessAssetType(files![id]),
    asset_file: `${ASSET_PART_PREFIX}${id}`,
  }));

  const content: Record<string, unknown> = {
    document: payload.document ?? '',
    assets,
  };
  fd.set('content', JSON.stringify(content));

  for (const id of assetIds) {
    const file = files![id];
    fd.set(`${ASSET_PART_PREFIX}${id}`, file, file.name || id);
  }

  return fd;
}

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

  getCourseHomeBySlug(slug: string): Promise<CourseHomeResponse> {
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
    return this.getMyCourses();
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
  ): Promise<unknown> {
    return apiClient.request(
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
  ): Promise<unknown> {
    return apiClient.request(
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
  ): Promise<unknown> {
    return apiClient.request(
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
  ): Promise<unknown> {
    return apiClient.request(
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
