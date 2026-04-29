import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Check,
  ChevronDown,
  Eye,
  EyeClosed,
  GripVertical,
  Home,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-react';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
  Input,
  PageFrame,
  Spinner,
} from '@shared/ui';
import type {
  AppCourseLesson,
  AppCourseSection,
  CourseHomeMeta,
  HomeworkAttemptStatus,
} from '@shared/api/courseApi';
import { courseApi } from '@shared/api/courseApi';
import { courseKeys, useCourseHomeBySlug } from '@shared/api/queries/courses';
import {
  useCreateLesson,
  useCreateSection,
  useDeleteLesson,
  useDeleteSection,
  usePatchSection,
  useToggleLessonType,
} from '@shared/api/mutations/courses';
import { useRole } from '@shared/lib/rbac/useRole';
import { cn } from '@shared/lib/utils';
import { AiChatPanel } from '../../../features/ai-chat';
import styles from './CourseLessonsPage.module.css';

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

const STREAK_FIRE_SRC = `${import.meta.env.BASE_URL}course/yellow-fire.svg`;

function StreakCard({ streakDays = 13 }: { streakDays?: number }) {
  return (
    <div className={cn(styles.sideCard, styles.streakCard)}>
      <div className={styles.streakCardLayout}>
        <div className={styles.streakCardTextCol}>
          <p className={styles.streakCardTitle}>
            Ваша серия
            <br />
            вебинаров
          </p>
          <p className={styles.streakCardSubtitle}>
            Не пропусти следующий,
            <br />
            чтобы серия росла
          </p>
        </div>
        <div className={styles.streakVisualCol}>
          <span className={styles.streakNumber}>{streakDays}</span>
          <img
            src={STREAK_FIRE_SRC}
            alt=""
            className={styles.streakFireImg}
            width={58}
            height={107}
            decoding="async"
          />
        </div>
      </div>
    </div>
  );
}

function StudentProgressCard({
  lessonsDone,
  lessonsTotal,
  homeworkDone,
  homeworkTotal,
}: {
  lessonsDone: number;
  lessonsTotal: number;
  homeworkDone: number;
  homeworkTotal: number;
}) {
  const lessonsPct =
    lessonsTotal > 0 ? Math.round((lessonsDone / lessonsTotal) * 100) : 0;
  const hwPct =
    homeworkTotal > 0 ? Math.round((homeworkDone / homeworkTotal) * 100) : 0;

  return (
    <div
      className={cn(
        styles.sideCard,
        styles.statSidebarCard,
        styles.studentProgressCard
      )}
    >
      <div className={styles.progressCardHead}>
        <span className={styles.progressLiveDot} aria-hidden />
        <p className={styles.progressCardTitle}>Ваш прогресс</p>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Пройдено уроков</span>
          <span className={styles.progressValue}>
            {lessonsDone}/{lessonsTotal}
          </span>
        </div>
        <div className={styles.progressTrack}>
          <div
            className={styles.progressFillStudent}
            style={{ width: `${lessonsPct}%` }}
          />
        </div>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Сдано заданий</span>
          <span className={styles.progressValue}>
            {homeworkDone}/{homeworkTotal}
          </span>
        </div>
        <div className={styles.progressTrack}>
          <div
            className={styles.progressFillStudent}
            style={{ width: `${hwPct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function StaffStatsCard() {
  return (
    <div className={styles.sideCard}>
      <p className={styles.sideCardTitle}>Статистика</p>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Посещаемость вебинаров</span>
          <span className={styles.progressValue}>50%</span>
        </div>
        <div className={styles.progressTrack}>
          <div className={styles.progressFillDark} style={{ width: '50%' }} />
        </div>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Сдача ДЗ</span>
          <span className={styles.progressValue}>50%</span>
        </div>
        <div className={styles.progressTrack}>
          <div className={styles.progressFillDark} style={{ width: '50%' }} />
        </div>
      </div>
    </div>
  );
}

function StudentStatusIcon({ done }: { done: boolean }) {
  if (done) {
    return (
      <span
        className={cn(styles.statusIcon, styles.statusIconDone)}
        aria-hidden
      >
        <Check size={14} strokeWidth={3} />
      </span>
    );
  }
  return (
    <span
      className={cn(styles.statusIcon, styles.statusIconPending)}
      aria-hidden
    >
      <span className={styles.statusIconPendingBars}>
        <span className={styles.statusIconPendingBar} />
        <span className={styles.statusIconPendingBar} />
      </span>
    </span>
  );
}

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const { hasAny } = useRole();
  const isStaff = hasAny('teacher', 'moderator');

  const homeQuery = useCourseHomeBySlug(slug);
  const { data: payload, isLoading, isError, refetch } = homeQuery;

  const title =
    (payload?.title && payload.title.trim() !== '' ? payload.title : null) ??
    slug?.replace(/-/g, ' ') ??
    'Курс';

  const { content, meta } = payload ?? {
    content: [],
    meta: { completed_sections_id: [], completed_lessons_id: [] },
  };

  const allLessons = useMemo(
    () => content.flatMap((s) => s.lessons),
    [content]
  );
  const lessonDetailQueries = useQueries({
    queries: allLessons.map((lesson) => ({
      queryKey: courseKeys.lesson(slug ?? '', lesson.slug),
      queryFn: () => courseApi.getLessonBySlug(slug ?? '', lesson.slug),
      enabled: Boolean(slug),
      staleTime: 30_000,
    })),
  });
  const homeworkSlugs = useMemo(() => {
    const slugs = new Set<string>();
    for (const lessonDetailQuery of lessonDetailQueries) {
      for (const homework of lessonDetailQuery.data?.homeworks ?? []) {
        if (homework.type === 'published') {
          slugs.add(homework.homework_slug);
        }
      }
    }
    return Array.from(slugs);
  }, [lessonDetailQueries]);
  const attemptQueries = useQueries({
    queries: homeworkSlugs.map((homeworkSlug) => ({
      queryKey: courseKeys.homeworkAttempt(homeworkSlug),
      queryFn: () => courseApi.getHomeworkAttempt(homeworkSlug),
      staleTime: 30_000,
    })),
  });
  const attemptStatusByHomeworkSlug = useMemo(() => {
    const map = new Map<string, HomeworkAttemptStatus>();
    for (let i = 0; i < homeworkSlugs.length; i += 1) {
      const slugItem = homeworkSlugs[i];
      const status = attemptQueries[i]?.data?.status;
      if (slugItem && status) {
        map.set(slugItem, status);
      }
    }
    return map;
  }, [attemptQueries, homeworkSlugs]);
  const lessonHomeworkStatus = useMemo(() => {
    const map = new Map<string, HomeworkAttemptStatus | null>();
    for (let i = 0; i < allLessons.length; i += 1) {
      const lesson = allLessons[i];
      const homeworks = lessonDetailQueries[i]?.data?.homeworks ?? [];
      if (homeworks.length === 0) {
        map.set(lesson.slug, null);
        continue;
      }
      const statuses = homeworks
        .filter((homework) => homework.type === 'published')
        .map((homework) => attemptStatusByHomeworkSlug.get(homework.homework_slug))
        .filter((status): status is HomeworkAttemptStatus => Boolean(status));
      if (statuses.includes('reviewed')) {
        map.set(lesson.slug, 'reviewed');
      } else if (statuses.includes('submitted')) {
        map.set(lesson.slug, 'submitted');
      } else {
        map.set(lesson.slug, 'draft');
      }
    }
    return map;
  }, [allLessons, attemptStatusByHomeworkSlug, lessonDetailQueries]);

  const lessonStats = useMemo(() => {
    const total = allLessons.length;
    const done = allLessons.filter((l) =>
      isLessonCompleted(l.lesson_id, meta.completed_lessons_id)
    ).length;
    return { done, total };
  }, [allLessons, meta.completed_lessons_id]);
  const homeworkStats = useMemo(() => {
    const total = homeworkSlugs.length;
    const done = Array.from(attemptStatusByHomeworkSlug.values()).filter(
      (status) => status === 'submitted' || status === 'reviewed'
    ).length;
    return { done, total };
  }, [attemptStatusByHomeworkSlug, homeworkSlugs.length]);

  const [openSections, setOpenSections] = useState<Set<string>>(
    () => new Set()
  );

  const toggleSection = (sectionId: string, open: boolean) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (open) next.add(sectionId);
      else next.delete(sectionId);
      return next;
    });
  };

  if (!slug) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>Не указан адрес курса.</p>
            <Button type="button" variant="outline" asChild>
              <Link to="/app">На главную</Link>
            </Button>
          </div>
        </div>
      </PageFrame>
    );
  }

  if (isLoading) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </PageFrame>
    );
  }

  if (isError || !payload) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>
              Не удалось загрузить программу курса. Проверьте, что вы записаны
              на курс, и попробуйте снова.
            </p>
            <Button type="button" onClick={() => void refetch()}>
              Попробовать снова
            </Button>
          </div>
        </div>
      </PageFrame>
    );
  }

  if (!content.length) {
    return (
      <PageFrame>
			<div className={styles.breadcrumbWrap}>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link
                    to="/app"
                    className={styles.homeLink}
                    aria-label="Домашняя"
                  >
                    <Home size={18} strokeWidth={2} />
                  </Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{title}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>
        <h1 className={styles.pageTitle}>{title}</h1>
        <div className={styles.layout}>
          <div className={styles.mainColumn}>
            <div className={styles.empty}>В этом курсе пока нет разделов.</div>
            {isStaff ? <AddSectionRow courseSlug={slug ?? ''} /> : null}
          </div>
          <aside className={styles.sidebar}>
            {isStaff ? (
              <StaffStatsCard />
            ) : (
              <>
                <StreakCard />
                <StudentProgressCard
                  lessonsDone={0}
                  lessonsTotal={0}
                  homeworkDone={0}
                  homeworkTotal={0}
                />
              </>
            )}
            <AiChatPanel courseSlug={slug} />
          </aside>
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
		<div className={styles.breadcrumbWrap}>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link
                  to="/app"
                  className={styles.homeLink}
                  aria-label="Домашняя"
                >
                  <Home size={18} strokeWidth={2} />
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{title}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <h1 className={styles.pageTitle}>{title}</h1>

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          {content.map((section) => (
            <SectionBlock
              key={section.section_id}
              section={section}
              courseSlug={slug ?? ''}
              isStaff={isStaff}
              meta={meta}
              homeworkStatusByLessonSlug={lessonHomeworkStatus}
              open={openSections.has(section.section_id)}
              onOpenChange={(o) => toggleSection(section.section_id, o)}
            />
          ))}

          {isStaff ? <AddSectionRow courseSlug={slug ?? ''} /> : null}
        </div>

        <aside className={styles.sidebar}>
          {isStaff ? (
            <StaffStatsCard />
          ) : (
            <>
              <StreakCard />
              <StudentProgressCard
                lessonsDone={lessonStats.done}
                lessonsTotal={lessonStats.total}
                homeworkDone={homeworkStats.done}
                homeworkTotal={homeworkStats.total}
              />
            </>
          )}
          <AiChatPanel courseSlug={slug} />
        </aside>
      </div>
    </PageFrame>
  );
}

function SectionStaffTools({
  canManageSection,
  editingTitle,
  onEditTitle,
  onDeleteSection,
  deletePending,
}: {
  canManageSection: boolean;
  editingTitle: boolean;
  onEditTitle: () => void;
  onDeleteSection: () => void;
  deletePending: boolean;
}) {
  return (
    <div
      className={styles.staffSectionTools}
      role="group"
      onClick={(e) => e.stopPropagation()}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className={styles.staffIconEditBtn}
        disabled={!canManageSection || editingTitle}
        title={
          canManageSection
            ? 'Редактировать название'
            : 'У раздела нет slug — обновите страницу или проверьте API'
        }
        onClick={onEditTitle}
      >
        <Pencil size={21} strokeWidth={2} />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className={styles.staffIconDeleteBtn}
        disabled={!canManageSection || deletePending}
        title={
          canManageSection
            ? 'Удалить раздел'
            : 'У раздела нет slug — обновите страницу или проверьте API'
        }
        onClick={onDeleteSection}
      >
        <Trash2 size={21} strokeWidth={2} />
      </Button>
    </div>
  );
}

function SectionBlock({
  section,
  courseSlug,
  isStaff,
  meta,
  homeworkStatusByLessonSlug,
  open,
  onOpenChange,
}: {
  section: AppCourseSection;
  courseSlug: string;
  isStaff: boolean;
  meta: CourseHomeMeta;
  homeworkStatusByLessonSlug: Map<string, HomeworkAttemptStatus | null>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
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

function LessonRow({
  lesson,
  sectionNumber,
  courseSlug,
  isStaff,
  lessonDone,
  homeworkStatus,
}: {
  lesson: AppCourseLesson;
  sectionNumber: number;
  courseSlug: string;
  isStaff: boolean;
  lessonDone: boolean;
  homeworkStatus: HomeworkAttemptStatus | null;
}) {
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
      <div className={cn(styles.lessonRow, styles.lessonRowStaff)}>
        <span className={styles.lessonDragHandleSlot}>
          <span className={styles.lessonDragHandle} aria-hidden>
            <GripVertical size={16} strokeWidth={2} />
          </span>
        </span>
        <Link
          to={lessonViewTo}
          className={cn(styles.lessonTitle, styles.lessonTitleLink)}
        >
          {lessonLabel}
        </Link>
        <div className={styles.staffLessonActions}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={styles.publishBtn}
            disabled={lessonCreatePending || toggleType.isPending}
            onClick={() =>
              toggleType.mutate({
                lessonSlug: lesson.slug,
                currentType: lesson.type,
              })
            }
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
            onClick={() =>
              navigate(
                `/app/courses/${courseSlug}/${encodeURIComponent(lesson.slug)}/edit`
              )
            }
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
            onClick={requestDeleteLesson}
          >
            <Trash2 size={21} strokeWidth={2} />
          </Button>
        </div>
      </div>
    );
  }

  const to = lessonViewTo;

  return (
    <Link to={to} className={cn(styles.lessonRow, styles.lessonRowStudent)}>
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

function AddSectionRow({ courseSlug }: { courseSlug: string }) {
  const [title, setTitle] = useState('');
  const [expanded, setExpanded] = useState(false);
  const createMutation = useCreateSection(courseSlug);

  useLayoutEffect(() => {
    if (!expanded) return;
    window.requestAnimationFrame(() => {
      document.getElementById('new-section-input')?.focus();
    });
  }, [expanded]);

  const submit = () => {
    const trimmed = title.trim();
    if (!trimmed) return;
    void (async () => {
      try {
        await createMutation.mutateAsync({ title: trimmed });
        setTitle('');
        setExpanded(false);
      } catch {
        return;
      }
    })();
  };

  const cancel = () => {
    setTitle('');
    setExpanded(false);
  };

  return (
    <div className={styles.inlineAddSection}>
      {!expanded ? (
        <div className={styles.addFlowCollapsed}>
          <Button
            type="button"
            variant="outline"
            className={styles.addSectionTriggerBtn}
            onClick={() => setExpanded(true)}
          >
            <Plus size={18} strokeWidth={2} />
            Добавить раздел
          </Button>
        </div>
      ) : (
        <div className={styles.addSectionExpanded}>
          <Input
            id="new-section-input"
            className={cn(
              styles.inlineAddSectionInput,
              styles.addFlowInputAnim
            )}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Название"
            disabled={createMutation.isPending}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit();
              if (e.key === 'Escape') cancel();
            }}
          />
          <div className={cn(styles.addFlowActions, styles.addFlowActionsAnim)}>
            <Button
              type="button"
              variant="primary"
              className={styles.addSectionSubmitBtn}
              disabled={!title.trim() || createMutation.isPending}
              onClick={submit}
            >
              {createMutation.isPending ? (
                <Spinner />
              ) : (
                <>
                  <Plus size={18} strokeWidth={2} />
                  Добавить раздел
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={createMutation.isPending}
              onClick={cancel}
            >
              Отмена
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
