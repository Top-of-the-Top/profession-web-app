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
  is_completed: boolean | null;
}

export interface AppCourseSection {
  section_id: string;
  section_number: number;
  title: string;
  slug?: string;
  lessons: AppCourseLesson[];
  type?: CourseContentType;
  section_completed: boolean | null;
}

export interface CourseHomeMetaStudent {
  role: 'student';
  lessons_completed: number;
  lessons_total: number;
  homeworks_submitted: number;
  homeworks_total: number;
  attendance_streak: number;
  course_rank_top_percent: number | null;
}

export interface CourseHomeMetaStaff {
  role: 'teacher_or_moderator';
  webinar_attendance_rate: number;
  homework_completion_rate: number;
}

export interface CourseHomeMetaUnknown {
  role: string;
}

export type CourseHomeMeta = CourseHomeMetaStudent | CourseHomeMetaStaff | CourseHomeMetaUnknown;

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

export type HomeworkAttemptStatusFull = 'not_started' | 'draft' | 'submitted' | 'reviewed';

export interface LessonHomework {
  homework_id: string;
  title: string;
  deadline: string;
  homework_slug: string;
  type: CourseContentType;
  attempt_status: HomeworkAttemptStatusFull | null;
  attempt_grade: number | null;
  attempt_max_points: number;
  percentile: number | null;
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

export interface HomeworkTaskReviewReviewer {
  first_name: string;
  last_name: string;
  avatar_url: string | null;
}

export interface HomeworkTaskReview {
  task_review_id: string;
  points: number;
  comment: string | null;
  reviewer: HomeworkTaskReviewReviewer | null;
  created_at: string;
  updated_at: string;
}

export interface HomeworkAttemptQuestionItem {
  type: 'question';
  question_id: string;
  answer_id: string;
  status: string;
  number: number;
  text: string;
  answer_options: string[];
  correct_ans: string | null;
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
  max_points: number;
  review: HomeworkTaskReview | null;
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
  asset_ids?: string[];
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

export interface HomeworkAttemptListItem {
  attempt_id: string;
  homework_id: string;
  deadline: string;
  homework_slug: string;
  status: HomeworkAttemptStatus;
  send_at: string | null;
  score: number | null;
  max_points: number | null;
}

// GET /api/v1/my-homeworks/ — student view
export interface MyHomeworkStudentItem {
  attempt_id: string;
  status: HomeworkAttemptStatus;
  homework_id: string;
  homework_slug: string;
  homework_title: string;
  deadline: string | null;
  course_slug: string;
  course_title: string;
  lesson_slug: string;
  lesson_title: string;
  grade: number | null;
  max_points: number | null;
  send_at: string | null;
}

// GET /api/v1/my-homeworks/ — teacher view
export interface MyHomeworkTeacherStudent {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface MyHomeworkTeacherAttempt {
  attempt_id: string;
  status: HomeworkAttemptStatus;
  homework_id: string;
  homework_slug: string;
  homework_title: string;
  course_slug: string;
  lesson_slug: string;
  grade: number | null;
  max_points: number | null;
  send_at: string | null;
  student: MyHomeworkTeacherStudent;
}

export type MyHomeworksResponse =
  | { my_attempts: { items: MyHomeworkStudentItem[] } }
  | { student_attempts: { items: MyHomeworkTeacherAttempt[] } };

export interface ReviewHomeworkAttemptItemPayload {
  task_answer_id: string;
  points: number;
  comment?: string | null;
}

export interface ReviewHomeworkAttemptPayload {
  attempt_id: string;
  items: ReviewHomeworkAttemptItemPayload[];
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
export type LessonRecordingKind = 'recording' | 'whiteboard_only';

export interface LessonRecording {
  recording_id: string;
  kind: LessonRecordingKind;
  started_at: string | null;
  ended_at: string | null;
  status: RecordingStatus;
  kinescope_upload_status: KinescopeUploadStatus;
  kinescope_embed_url: string;
  whiteboard_pdf_url: string;
}

export interface LessonMetaStudent {
  role: 'student';
  watched_ratio: number;
  homeworks_submitted: number;
  homeworks_total: number;
  is_completed: boolean;
}

export interface LessonMetaStaff {
  role: 'teacher_or_moderator';
  attended_count: number;
  attended_total: number;
  homework_submitted_count: number;
  homework_submitted_total: number;
}

export interface LessonMetaUnknown {
  role: string;
}

export type LessonMeta = LessonMetaStudent | LessonMetaStaff | LessonMetaUnknown;

export interface CourseLessonDetail {
  lesson_id: number;
  title: string;
  course_title: string | null;
  document: string;
  scheduled_at: string | null;
  started_at: string | null;
  webinar_status: WebinarStatus | null;
  recordings: LessonRecording[];
  homeworks: LessonHomework[];
  meta: LessonMeta;
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
}

export interface LessonPatchPayload {
  title?: string;
  section?: string | null;
  type?: CourseContentType;
  date_time?: string | null;
  document?: string;
}

export interface CoursePatchPayload {
  title?: string;
  sub_title?: string;
  description?: string;
  price?: number;
  type?: CourseContentType;
  cover_asset_id?: string | null;
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
  course_title?: unknown;
  content: {
    document?: string;
    recording_url?: string | null;
    scheduled_at?: string | null;
    started_at?: string | null;
    webinar_status?: WebinarStatus | null;
    whiteboard_pdf_url?: string | null;
    kinescope_embed_url?: string | null;
    kinescope_upload_status?: KinescopeUploadStatus | null;
    recordings?: Array<{
      recording_id?: string;
      kind?: LessonRecordingKind;
      started_at?: string | null;
      ended_at?: string | null;
      status?: RecordingStatus;
      kinescope_upload_status?: KinescopeUploadStatus | null;
      kinescope_embed_url?: string | null;
      whiteboard_pdf_url?: string | null;
    }>;
    homeworks?: Array<{
      homework_id?: unknown;
      title?: unknown;
      deadline?: unknown;
      homework_slug?: unknown;
      type?: unknown;
      attempt_status?: unknown;
      attempt_grade?: unknown;
      attempt_max_points?: unknown;
      percentile?: unknown;
    }>;
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
  max_points?: unknown;
  review?: {
    task_review_id?: unknown;
    points?: unknown;
    comment?: unknown;
    reviewer?: {
      first_name?: unknown;
      last_name?: unknown;
      avatar_url?: unknown;
    } | null;
    created_at?: unknown;
    updated_at?: unknown;
  } | null;
  file_attachments?: unknown;
};

export type RawHomeworkAttempt = {
  homework_id?: unknown;
  attempt_id?: unknown;
  status?: unknown;
  deadline?: unknown;
  score?: unknown;
  max_points?: unknown;
  send_at?: unknown;
  homework_slug?: unknown;
  items?: unknown;
};
