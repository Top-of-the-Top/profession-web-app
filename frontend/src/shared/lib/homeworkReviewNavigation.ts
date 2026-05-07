export const HOMEWORK_REVIEW_FROM = 'homeworkReviewFrom' as const;

export type HomeworkReviewNavigateState = {
  [HOMEWORK_REVIEW_FROM]?: string;
};

function isSafeInternalPath(value: string): boolean {
  if (!value.startsWith('/app')) return false;
  if (value.startsWith('//')) return false;
  return true;
}

export function homeworkReviewNavigateState(fromPathWithSearch: string): HomeworkReviewNavigateState {
  return { [HOMEWORK_REVIEW_FROM]: fromPathWithSearch };
}

export function getHomeworkReviewBackHref(
  state: unknown,
  courseSlug: string,
  lessonSlug: string,
): string {
  const raw = (state as HomeworkReviewNavigateState | null)?.[HOMEWORK_REVIEW_FROM];
  if (typeof raw === 'string' && isSafeInternalPath(raw)) {
    return raw;
  }
  const q = new URLSearchParams({ course_slug: courseSlug, lesson_slug: lessonSlug });
  return `/app/homeworks?${q.toString()}`;
}
