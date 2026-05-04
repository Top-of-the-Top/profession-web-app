import { Eye, EyeClosed, GripVertical, Pencil, Trash2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import type { AppCourseLesson, HomeworkAttemptStatus } from '@shared/api/courseApi';
import { useDeleteLesson, useToggleLessonType } from '@shared/api/mutations/courses';
import { Button } from '@shared/ui';
import { cn } from '@shared/lib/utils';
import { StudentStatusIcon } from './StudentStatusIcon';
import styles from '../CourseLessonsPage.module.css';

interface LessonRowProps {
  lesson: AppCourseLesson;
  sectionNumber: number;
  courseSlug: string;
  isStaff: boolean;
  lessonDone: boolean;
  homeworkStatus: HomeworkAttemptStatus | null;
}

export function LessonRow({
  lesson,
  sectionNumber,
  courseSlug,
  isStaff,
  lessonDone,
  homeworkStatus,
}: LessonRowProps) {
  const navigate = useNavigate();
  const toggleType = useToggleLessonType(courseSlug);
  const deleteLesson = useDeleteLesson(courseSlug);
  const lessonLabel = `${sectionNumber}.${lesson.lesson_number} ${lesson.title}`;
  const published = lesson.type !== 'draft';
  const lessonCreatePending = lesson.lesson_id.startsWith('optimistic:');
  const lessonViewTo = `/app/courses/${courseSlug}/${encodeURIComponent(lesson.slug)}`;

  const requestDeleteLesson = () => {
    if (
      !window.confirm(
        `Урок «${lesson.title}» будет удалён без возможности восстановления. Продолжить?`
      )
    ) {
      return;
    }
    void deleteLesson.mutateAsync(lesson.slug);
  };

  if (isStaff) {
    return (
      <div
        className={cn(styles.lessonRow, styles.lessonRowStaff)}
        role="button"
        tabIndex={0}
        onClick={() => {
          navigate(lessonViewTo);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            navigate(lessonViewTo);
          }
        }}
      >
        <span className={styles.lessonDragHandleSlot}>
          <span className={styles.lessonDragHandle} aria-hidden>
            <GripVertical size={16} strokeWidth={2} />
          </span>
        </span>
        <span className={cn(styles.lessonTitle, styles.lessonTitleLink)}>
          {lessonLabel}
        </span>
        <div className={styles.staffLessonActions}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={styles.publishBtn}
            disabled={lessonCreatePending || toggleType.isPending}
            onClick={(event) => {
              event.stopPropagation();
              toggleType.mutate({
                lessonSlug: lesson.slug,
                currentType: lesson.type,
              });
            }}
          >
            {published ? 'Отозвать' : 'Опубликовать'}
          </Button>
          <span
            className={cn(
              styles.staffEyeSlot,
              published ? styles.staffEyePublished : styles.staffEyeDraft
            )}
            aria-hidden
          >
            {published ? (
              <Eye size={18} strokeWidth={2} />
            ) : (
              <EyeClosed size={18} strokeWidth={2} />
            )}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className={styles.staffIconEditBtn}
            disabled={lessonCreatePending}
            onClick={(event) => {
              event.stopPropagation();
              navigate(
                `/app/courses/${courseSlug}/${encodeURIComponent(lesson.slug)}/edit`
              );
            }}
          >
            <Pencil size={21} strokeWidth={2} />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className={styles.staffIconDeleteBtn}
            disabled={lessonCreatePending || deleteLesson.isPending}
            title="Удалить урок"
            onClick={(event) => {
              event.stopPropagation();
              requestDeleteLesson();
            }}
          >
            <Trash2 size={21} strokeWidth={2} />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Link to={lessonViewTo} className={cn(styles.lessonRow, styles.lessonRowStudent)}>
      <span className={styles.lessonTitle}>{lessonLabel}</span>
      <div className={styles.lessonStudentState}>
        {homeworkStatus && (
          <span
            className={cn(
              styles.lessonHomeworkBadge,
              homeworkStatus === 'reviewed'
                ? styles.lessonHomeworkBadgeReviewed
                : homeworkStatus === 'submitted'
                  ? styles.lessonHomeworkBadgeSubmitted
                  : styles.lessonHomeworkBadgeDraft
            )}
          >
            {homeworkStatus === 'reviewed'
              ? 'ДЗ проверено'
              : homeworkStatus === 'submitted'
                ? 'ДЗ отправлено'
                : 'ДЗ не сдано'}
          </span>
        )}
        <StudentStatusIcon done={lessonDone} />
      </div>
    </Link>
  );
}
