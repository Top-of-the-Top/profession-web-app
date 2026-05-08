import { Eye, EyeClosed, GripVertical, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { AppCourseLesson } from '@shared/api/courseApi';
import { useDeleteLesson, useToggleLessonType } from '@shared/api/mutations/courses';
import { Button, Modal } from '@shared/ui';
import { cn } from '@shared/lib/utils';
import { StudentStatusIcon } from './StudentStatusIcon';
import styles from '../CourseLessonsPage.module.css';

interface LessonRowProps {
  lesson: AppCourseLesson;
  sectionNumber: number;
  courseSlug: string;
  isStaff: boolean;
  lessonDone: boolean;
}

export function LessonRow({
  lesson,
  sectionNumber,
  courseSlug,
  isStaff,
  lessonDone,
}: LessonRowProps) {
  const navigate = useNavigate();
  const toggleType = useToggleLessonType(courseSlug);
  const deleteLesson = useDeleteLesson(courseSlug);
  const lessonLabel = `${sectionNumber}.${lesson.lesson_number} ${lesson.title}`;
  const published = lesson.type !== 'draft';
  const lessonCreatePending = lesson.lesson_id.startsWith('optimistic:');
  const lessonViewTo = `/app/courses/${courseSlug}/${encodeURIComponent(lesson.slug)}`;
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const confirmDeleteLesson = () => {
    void deleteLesson.mutateAsync(lesson.slug);
    setDeleteDialogOpen(false);
  };

  if (isStaff) {
    return (
      <>
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
                setDeleteDialogOpen(true);
              }}
            >
              <Trash2 size={21} strokeWidth={2} />
            </Button>
          </div>
        </div>
        <Modal
          open={isDeleteDialogOpen}
          onClose={() => {
            if (!deleteLesson.isPending) {
              setDeleteDialogOpen(false);
            }
          }}
          panelClassName={styles.deleteLessonDialog}
          closeOnBackdrop={!deleteLesson.isPending}
        >
          <h3 className={styles.deleteLessonDialogTitle}>Удалить урок?</h3>
          <p className={styles.deleteLessonDialogDescription}>
            Урок «{lesson.title}» будет удалён без возможности восстановления.
          </p>
          <div className={styles.deleteLessonDialogActions}>
            <Button
              type="button"
              variant="outline"
              disabled={deleteLesson.isPending}
              onClick={() => setDeleteDialogOpen(false)}
            >
              Отмена
            </Button>
            <Button
              type="button"
              disabled={deleteLesson.isPending}
              onClick={confirmDeleteLesson}
            >
              {deleteLesson.isPending ? 'Удаление...' : 'Удалить'}
            </Button>
          </div>
        </Modal>
      </>
    );
  }

  return (
    <Link to={lessonViewTo} className={cn(styles.lessonRow, styles.lessonRowStudent)}>
      <span className={styles.lessonTitle}>{lessonLabel}</span>
      <div className={styles.lessonStudentState}>
        <StudentStatusIcon done={lessonDone} />
      </div>
    </Link>
  );
}
