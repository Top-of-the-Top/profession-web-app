import type {
  Course,
  CourseApiAnswer,
  CourseDTO,
  CourseHomeResponse,
  CourseLessonDetail,
  HomeworkAttempt,
  HomeworkAttemptAttachment,
  HomeworkAttemptItem,
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

function normalizeIdList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item));
}

export function normalizeCourseHomeResponse(raw: RawCourseHomeResponse): CourseHomeResponse {
  const rawContent = raw.content;
  const content = Array.isArray(rawContent)
    ? rawContent
    : rawContent != null
      ? [rawContent]
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

export function normalizeLessonDetailRead(raw: RawLessonDetailResponse): CourseLessonDetail {
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
      user_answer:
        question.user_answer == null ? null : String(question.user_answer),
      max_points: Number(question.max_points ?? 0),
    };
  }

  if ((item as { type?: unknown }).type === 'task') {
    const task = item as RawHomeworkAttemptTaskItem & { id?: unknown };
    return {
      type: 'task',
      task_id: String(task.task_id ?? task.id ?? ''),
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

