import { useEffect, useLayoutEffect, useState } from 'react';
import { ChevronDown, GripVertical, Plus } from 'lucide-react';
import {
  Button,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  Input,
  Spinner,
} from '@shared/ui';
import type {
  AppCourseSection,
  CourseHomeMeta,
  HomeworkAttemptStatus,
} from '@shared/api/courseApi';
import {
  useCreateLesson,
  useDeleteSection,
  usePatchSection,
} from '@shared/api/mutations/courses';
import { cn } from '@shared/lib/utils';
import { SectionStaffTools } from './SectionStaffTools';
import { StudentStatusIcon } from './StudentStatusIcon';
import { LessonRow } from './LessonRow';
import styles from '../CourseLessonsPage.module.css';

function idKey(id: number | string): string {
  return String(id);
}

function isLessonCompleted(lessonId: string, completed: string[]): boolean {
  const key = idKey(lessonId);
  return completed.some((c) => String(c) === key);
}

function isSectionCompleted(sectionId: string, completed: string[]): boolean {
  return completed.some((c) => String(c) === sectionId);
}

interface SectionBlockProps {
  section: AppCourseSection;
  courseSlug: string;
  isStaff: boolean;
  meta: CourseHomeMeta;
  homeworkStatusByLessonSlug: Map<string, HomeworkAttemptStatus | null>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SectionBlock({
  section,
  courseSlug,
  isStaff,
  meta,
  homeworkStatusByLessonSlug,
  open,
  onOpenChange,
}: SectionBlockProps) {
  const [editingTitle, setEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState(section.title);
  const [addingLesson, setAddingLesson] = useState(false);
  const [newLessonTitle, setNewLessonTitle] = useState('');
  const patchSection = usePatchSection(courseSlug);
  const deleteSectionMutation = useDeleteSection(courseSlug);
  const createLesson = useCreateLesson(courseSlug);
  const sectionDone = isSectionCompleted(
    section.section_id,
    meta.completed_sections_id
  );

  const sectionSlug = section.slug?.trim() ?? '';
  const canManageSection = Boolean(sectionSlug);

  useEffect(() => {
    if (!editingTitle) setDraftTitle(section.title);
  }, [section.title, editingTitle]);

  useLayoutEffect(() => {
    if (!addingLesson) return;
    const id = `new-lesson-input-${idKey(section.section_id)}`;
    window.requestAnimationFrame(() => {
      document.getElementById(id)?.focus();
    });
  }, [addingLesson, section.section_id]);

  const saveSectionTitle = () => {
    const trimmed = draftTitle.trim();
    if (!trimmed || !canManageSection) return;
    void (async () => {
      try {
        await patchSection.mutateAsync({
          sectionSlug,
          payload: { title: trimmed },
        });
        setEditingTitle(false);
      } catch {
        return;
      }
    })();
  };

  const cancelSectionTitleEdit = () => {
    setDraftTitle(section.title);
    setEditingTitle(false);
  };

  const requestDeleteSection = () => {
    if (!canManageSection) return;
    if (
      !window.confirm(
        `Раздел «${section.title}» и все его уроки будут удалены без возможности восстановления. Продолжить?`
      )
    ) {
      return;
    }
    void deleteSectionMutation.mutateAsync(sectionSlug);
  };

  const submitNewLesson = () => {
    const trimmed = newLessonTitle.trim();
    if (!trimmed) return;
    void (async () => {
      try {
        await createLesson.mutateAsync({
          title: trimmed,
          section: section.section_id,
        });
        setNewLessonTitle('');
        setAddingLesson(false);
      } catch {
        return;
      }
    })();
  };

  const cancelNewLesson = () => {
    setNewLessonTitle('');
    setAddingLesson(false);
  };

  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <div className={styles.sectionCard}>
        <div className={styles.sectionCardWrapper}>
          <div className={styles.sectionHeader}>
            <span className={styles.dragHandleSlot} aria-hidden>
              {isStaff ? (
                <span className={styles.dragHandle}>
                  <GripVertical size={18} strokeWidth={2} />
                </span>
              ) : null}
            </span>

            {isStaff && editingTitle ? (
              <div className={styles.sectionTitleEdit}>
                <Input
                  className={styles.sectionTitleInput}
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  placeholder="Название раздела"
                  disabled={patchSection.isPending}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveSectionTitle();
                    if (e.key === 'Escape') cancelSectionTitleEdit();
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  disabled={
                    !draftTitle.trim() ||
                    patchSection.isPending ||
                    !canManageSection
                  }
                  onClick={saveSectionTitle}
                >
                  {patchSection.isPending ? <Spinner /> : 'Сохранить'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={patchSection.isPending}
                  onClick={cancelSectionTitleEdit}
                >
                  Отмена
                </Button>
              </div>
            ) : (
              <CollapsibleTrigger asChild>
                <button type="button" className={styles.sectionTitleBtn}>
                  <span className={styles.sectionTitleText}>
                    {section.section_number}. {section.title}
                  </span>
                </button>
              </CollapsibleTrigger>
            )}

            {isStaff ? (
              <SectionStaffTools
                canManageSection={canManageSection}
                editingTitle={editingTitle}
                onEditTitle={() => {
                  if (!canManageSection) return;
                  setDraftTitle(section.title);
                  setEditingTitle(true);
                }}
                onDeleteSection={requestDeleteSection}
                deletePending={deleteSectionMutation.isPending}
              />
            ) : (
              <StudentStatusIcon done={sectionDone} />
            )}

            <CollapsibleTrigger asChild>
              <button
                type="button"
                className={styles.chevronBtn}
                aria-label={open ? 'Свернуть раздел' : 'Развернуть раздел'}
              >
                <ChevronDown
                  size={22}
                  strokeWidth={2}
                  className={cn(
                    styles.sectionChevron,
                    open && styles.sectionChevronOpen
                  )}
                />
              </button>
            </CollapsibleTrigger>
          </div>

          <CollapsibleContent className={styles.sectionCollapsibleContent}>
            <div className={styles.sectionBody}>
              {section.lessons.map((lesson) => (
                <LessonRow
                  key={idKey(lesson.lesson_id)}
                  lesson={lesson}
                  sectionNumber={section.section_number}
                  courseSlug={courseSlug}
                  isStaff={isStaff}
                  lessonDone={isLessonCompleted(
                    lesson.lesson_id,
                    meta.completed_lessons_id
                  )}
                  homeworkStatus={homeworkStatusByLessonSlug.get(lesson.slug) ?? null}
                />
              ))}

              {isStaff && addingLesson ? (
                <div className={styles.inlineAddLesson}>
                  <Input
                    id={`new-lesson-input-${idKey(section.section_id)}`}
                    className={cn(
                      styles.inlineAddLessonInput,
                      styles.addFlowInputAnim
                    )}
                    value={newLessonTitle}
                    onChange={(e) => setNewLessonTitle(e.target.value)}
                    placeholder="Название"
                    disabled={createLesson.isPending}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') submitNewLesson();
                      if (e.key === 'Escape') cancelNewLesson();
                    }}
                  />
                  <div
                    className={cn(
                      styles.addFlowActions,
                      styles.addFlowActionsAnim
                    )}
                  >
                    <Button
                      type="button"
                      size="sm"
                      disabled={
                        !newLessonTitle.trim() || createLesson.isPending
                      }
                      onClick={submitNewLesson}
                    >
                      {createLesson.isPending ? <Spinner /> : 'Создать'}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={createLesson.isPending}
                      onClick={cancelNewLesson}
                    >
                      Отмена
                    </Button>
                  </div>
                </div>
              ) : null}
              {isStaff && !addingLesson ? (
                <div className={styles.addFlowCollapsed}>
                  <button
                    type="button"
                    className={styles.addLessonZone}
                    onClick={() => setAddingLesson(true)}
                  >
                    <Plus size={18} strokeWidth={2} />
                    Добавить урок
                  </button>
                </div>
              ) : null}
            </div>
          </CollapsibleContent>
        </div>
      </div>
    </Collapsible>
  );
}
