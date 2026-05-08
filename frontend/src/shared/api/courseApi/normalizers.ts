import type {
  Course,
  CourseApiAnswer,
  CourseDTO,
  CourseHomeMeta,
  CourseHomeResponse,
  CourseLessonDetail,
  HomeworkAttempt,
  HomeworkAttemptAttachment,
  HomeworkAttemptListItem,
  HomeworkAttemptItem,
  HomeworkTaskReview,
  LessonHomework,
  LessonMeta,
  LessonRecording,
  RawCourseBySlugResponse,
  RawCourseHomeResponse,
  RawCoursesResponse,
  RawHomeworkAttempt,
  RawHomeworkAttemptAttachment,
  RawHomeworkAttemptQuestionItem,
  RawHomeworkAttemptTaskItem,
  RawLessonDetailResponse,
  RecordingStatus,
} from './types';

function normalizeLessonRecordings(
  content: RawLessonDetailResponse['content'],
): LessonRecording[] {
  const list = Array.isArray(content.recordings) ? content.recordings : [];
  if (list.length > 0) {
    return list.map((recording) => ({
      recording_id: String(recording.recording_id ?? ''),
      kind: recording.kind ?? 'recording',
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
      kind: 'recording',
      started_at: content.started_at ?? null,
      ended_at: null,
      status: fallbackStatus,
      kinescope_upload_status: content.kinescope_upload_status ?? 'none',
      kinescope_embed_url: content.kinescope_embed_url ?? '',
      whiteboard_pdf_url: content.whiteboard_pdf_url ?? '',
    },
  ];
}

export function normalizeCoursesResponse(raw: RawCoursesResponse): CourseApiAnswer {
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

function toCourseDTOFromRecord(c: Record<string, unknown>): CourseDTO | null {
  if (typeof c.slug !== 'string' || typeof c.title !== 'string') return null;
  return {
    course_id: String(c.course_id ?? ''),
    title: c.title,
    sub_title: String(c.sub_title ?? ''),
    image_url: String(c.image_url ?? ''),
    price: Number(c.price ?? 0),
    slug: c.slug,
  };
}

export function normalizeMyCoursesList(raw: unknown): CourseDTO[] {
  if (!Array.isArray(raw)) return [];
  const out: CourseDTO[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const o = item as Record<string, unknown>;
    if (o.course && typeof o.course === 'object') {
      const nested = toCourseDTOFromRecord(o.course as Record<string, unknown>);
      if (nested) out.push(nested);
      continue;
    }
    const flat = toCourseDTOFromRecord(o);
    if (flat) out.push(flat);
  }
  return out;
}

export function normalizeCourseBySlugResponse(raw: RawCourseBySlugResponse): Course {
  const c = 'course' in raw ? raw.course : raw;
  return {
    ...c,
    course_id: String(c.course_id),
    last_modified_by: c.last_modified_by ?? null,
  };
}

function normalizeBoolNull(value: unknown): boolean | null {
  if (value === true || value === false) return value;
  return null;
}

function normalizeCourseHomeMeta(raw: unknown): CourseHomeMeta {
  const obj =
    raw != null && typeof raw === 'object' && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : {};

  const role = typeof obj.role === 'string' ? obj.role : '';

  if (role === 'student') {
    return {
      role: 'student',
      lessons_completed: Number(obj.lessons_completed ?? 0),
      lessons_total: Number(obj.lessons_total ?? 0),
      homeworks_submitted: Number(obj.homeworks_submitted ?? 0),
      homeworks_total: Number(obj.homeworks_total ?? 0),
      attendance_streak: Number(obj.attendance_streak ?? 0),
      course_rank_top_percent:
        obj.course_rank_top_percent == null ? null : Number(obj.course_rank_top_percent),
    };
  }

  if (role === 'teacher_or_moderator') {
    return {
      role: 'teacher_or_moderator',
      webinar_attendance_rate: Number(obj.webinar_attendance_rate ?? 0),
      homework_completion_rate: Number(obj.homework_completion_rate ?? 0),
    };
  }

  return { role };
}

export function normalizeCourseHomeResponse(raw: RawCourseHomeResponse): CourseHomeResponse {
  const rawContent = raw.content;
  const contentArr = Array.isArray(rawContent)
    ? rawContent
    : rawContent != null
      ? [rawContent]
      : [];

  const content = contentArr.map((section) => ({
    ...section,
    section_completed: normalizeBoolNull((section as unknown as Record<string, unknown>).section_completed),
    lessons: Array.isArray(section.lessons)
      ? section.lessons.map((lesson) => ({
          ...lesson,
          is_completed: normalizeBoolNull((lesson as unknown as Record<string, unknown>).is_completed),
        }))
      : [],
  }));

  return {
    course_id: String(raw.course_id ?? ''),
    title: String(raw.title ?? ''),
    content,
    meta: normalizeCourseHomeMeta(raw.meta),
  };
}

function normalizeLessonHomework(raw: Record<string, unknown>): LessonHomework {
  const attemptStatusRaw = raw.attempt_status;
  const validStatuses = ['not_started', 'draft', 'submitted', 'reviewed'] as const;
  const attempt_status =
    typeof attemptStatusRaw === 'string' &&
    (validStatuses as readonly string[]).includes(attemptStatusRaw)
      ? (attemptStatusRaw as LessonHomework['attempt_status'])
      : null;

  return {
    homework_id: String(raw.homework_id ?? ''),
    title: String(raw.title ?? ''),
    deadline: String(raw.deadline ?? ''),
    homework_slug: String(raw.homework_slug ?? ''),
    type: raw.type === 'draft' ? 'draft' : 'published',
    attempt_status,
    attempt_grade: raw.attempt_grade == null ? null : Number(raw.attempt_grade),
    attempt_max_points: Number(raw.attempt_max_points ?? 0),
    percentile: raw.percentile == null ? null : Number(raw.percentile),
  };
}

function normalizeLessonMeta(raw: unknown): LessonMeta {
  const obj =
    raw != null && typeof raw === 'object' && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : {};

  const role = typeof obj.role === 'string' ? obj.role : '';

  if (role === 'student') {
    return {
      role: 'student',
      watched_ratio: Number(obj.watched_ratio ?? 0),
      homeworks_submitted: Number(obj.homeworks_submitted ?? 0),
      homeworks_total: Number(obj.homeworks_total ?? 0),
      is_completed: Boolean(obj.is_completed),
    };
  }

  if (role === 'teacher_or_moderator') {
    return {
      role: 'teacher_or_moderator',
      attended_count: Number(obj.attended_count ?? 0),
      attended_total: Number(obj.attended_total ?? 0),
      homework_submitted_count: Number(obj.homework_submitted_count ?? 0),
      homework_submitted_total: Number(obj.homework_submitted_total ?? 0),
    };
  }

  return { role };
}

export function normalizeLessonDetailRead(raw: RawLessonDetailResponse): CourseLessonDetail {
  const c = raw.content ?? {};
  const homeworksRaw = Array.isArray(c.homeworks) ? c.homeworks : [];
  return {
    lesson_id: raw.lesson_id,
    title: raw.title,
    document: c.document ?? '',
    started_at: c.started_at ?? null,
    webinar_status: c.webinar_status ?? null,
    recordings: normalizeLessonRecordings(c),
    homeworks: homeworksRaw.map((hw) =>
      normalizeLessonHomework(hw as Record<string, unknown>),
    ),
    meta: normalizeLessonMeta(raw.meta),
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
    const question = item as RawHomeworkAttemptQuestionItem & { id?: unknown };
    return {
      type: 'question',
      question_id: String(question.question_id ?? question.id ?? ''),
      answer_id: String(question.answer_id ?? ''),
      status: String(question.status ?? ''),
      number: Number(question.number ?? 0),
      text: String(question.text ?? ''),
      answer_options: Array.isArray(question.answer_options)
        ? question.answer_options.map((option) => String(option))
        : [],
      correct_ans:
        (question as { correct_ans?: unknown }).correct_ans == null
          ? null
          : String((question as { correct_ans?: unknown }).correct_ans),
      user_answer:
        question.user_answer == null ? null : String(question.user_answer),
      max_points: Number(question.max_points ?? 0),
    };
  }

  if ((item as { type?: unknown }).type === 'task') {
    const task = item as RawHomeworkAttemptTaskItem & { id?: unknown };
    let review: HomeworkTaskReview | null = null;
    if (task.review && typeof task.review === 'object') {
      const rawReview = task.review;
      const reviewerValue =
        rawReview.reviewer && typeof rawReview.reviewer === 'object'
          ? {
              first_name: String(rawReview.reviewer.first_name ?? ''),
              last_name: String(rawReview.reviewer.last_name ?? ''),
              avatar_url:
                rawReview.reviewer.avatar_url == null
                  ? null
                  : String(rawReview.reviewer.avatar_url),
            }
          : null;
      review = {
        task_review_id: String(rawReview.task_review_id ?? ''),
        points: Number(rawReview.points ?? 0),
        comment: rawReview.comment == null ? null : String(rawReview.comment),
        reviewer: reviewerValue,
        created_at: String(rawReview.created_at ?? ''),
        updated_at: String(rawReview.updated_at ?? ''),
      };
    }
    return {
      type: 'task',
      task_id: String(task.task_id ?? task.id ?? ''),
      answer_id: String(task.answer_id ?? ''),
      status: String(task.status ?? ''),
      number: Number(task.number ?? 0),
      text: String(task.text ?? ''),
      user_answer: task.user_answer == null ? null : String(task.user_answer),
      max_points: Number(task.max_points ?? 0),
      review,
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

export function normalizeHomeworkAttempt(raw: RawHomeworkAttempt): HomeworkAttempt {
  const rawWithType = raw as RawHomeworkAttempt & { type?: unknown };
  const normalizedStatus = String(raw.status ?? rawWithType.type ?? 'draft');
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

export function normalizeHomeworkAttemptsList(raw: unknown): HomeworkAttemptListItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    const row = (item ?? {}) as RawHomeworkAttempt;
    const statusRaw = String(row.status ?? 'draft');
    const status =
      statusRaw === 'submitted' || statusRaw === 'reviewed' ? statusRaw : 'draft';
    return {
      attempt_id: String(row.attempt_id ?? ''),
      homework_id: String(row.homework_id ?? ''),
      deadline: String(row.deadline ?? ''),
      homework_slug: String(row.homework_slug ?? ''),
      status,
      send_at: row.send_at == null ? null : String(row.send_at),
      score: row.score == null ? null : Number(row.score),
      max_points: row.max_points == null ? null : Number(row.max_points),
    };
  });
}

