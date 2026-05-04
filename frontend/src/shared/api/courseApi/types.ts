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

export interface CourseItemWriteResponse {
  id: string;
}

export type RawCoursesResponse = Course[] | CourseApiAnswer;
export type RawCourseBySlugResponse = Course | { course: Course };
export type RawCourseHomeResponse = Partial<CourseHomeResponse> & {
  content?: AppCourseSection | AppCourseSection[];
  meta?: Record<string, unknown>;
};

export type RawLessonDetailResponse = {
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

export type RawHomeworkAttemptAttachment = {
  attachment_id?: unknown;
  file_name?: unknown;
  file_url?: unknown;
  file_size?: unknown;
  file_extension?: unknown;
  file_format?: unknown;
};

export type RawHomeworkAttemptQuestionItem = {
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

export type RawHomeworkAttemptTaskItem = {
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

export type RawHomeworkAttempt = {
  homework_id?: unknown;
  attempt_id?: unknown;
  status?: unknown;
  deadline?: unknown;
  score?: unknown;
  max_points?: unknown;
  items?: unknown;
};
