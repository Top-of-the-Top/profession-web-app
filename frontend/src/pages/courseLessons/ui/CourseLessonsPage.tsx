import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  Check,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Flame,
  GripVertical,
  Home,
  Pencil,
  Pause,
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
  PageTransition,
  Spinner,
} from '@shared/ui';
import type {
  AppCourseLesson,
  AppCourseSection,
  CourseHomeMeta,
} from '@shared/api/courseApi';
import { useCourseHomeBySlug } from '@shared/api/queries/courses';
import {
  useCreateLesson,
  useCreateSection,
  useDeleteLesson,
  useDeleteSection,
  usePatchSection,
  useToggleLessonType,
  useToggleSectionType,
} from '@shared/api/mutations/courses';
import { useRole } from '@shared/lib/rbac/useRole';
import { cn } from '@shared/lib/utils';
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

function findSectionIdForLessonSlug(
  sections: AppCourseSection[],
  lessonSlug: string | null,
): string | null {
  if (!lessonSlug) return null;
  const s = sections.find((sec) =>
    sec.lessons.some((l) => l.slug === lessonSlug),
  );
  return s?.section_id ?? null;
}

function StreakCard() {
  return (
    <div className={styles.sideCard}>
      <p className={styles.sideCardTitle}>Ваша серия вебинаров</p>
      <p className={styles.sideCardHint}>
        Не пропусти следующий, чтобы серия росла
      </p>
      <div className={styles.streakRow}>
        <span className={styles.streakNumber}>13</span>
        <Flame className={styles.streakFlame} size={28} strokeWidth={1.75} />
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
    <div className={styles.sideCard}>
      <p className={styles.sideCardTitle}>Ваш прогресс</p>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Пройдено уроков</span>
          <span className={styles.progressValue}>
            {lessonsDone}/{lessonsTotal}
          </span>
        </div>
        <div className={styles.progressTrack}>
          <div
            className={styles.progressFill}
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
            className={styles.progressFill}
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
      <span className={cn(styles.statusIcon, styles.statusIconDone)} aria-hidden>
        <Check size={14} strokeWidth={3} />
      </span>
    );
  }
  return (
    <span
      className={cn(styles.statusIcon, styles.statusIconPending)}
      aria-hidden
    >
      <Pause size={14} strokeWidth={2.5} />
    </span>
  );
}

type CourseLessonsLocationState = { highlightLesson?: string };

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const location = useLocation();
  const highlightLesson =
    (location.state as CourseLessonsLocationState | null)?.highlightLesson ??
    null;
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
    [content],
  );

  const lessonStats = useMemo(() => {
    const total = allLessons.length;
    const done = allLessons.filter((l) =>
      isLessonCompleted(l.lesson_id, meta.completed_lessons_id),
    ).length;
    return { done, total };
  }, [allLessons, meta.completed_lessons_id]);

  const [openSections, setOpenSections] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    if (!highlightLesson || !content.length) return;
    const sid = findSectionIdForLessonSlug(content, highlightLesson);
    if (sid != null) {
      setOpenSections((prev) => new Set(prev).add(sid));
    }
  }, [highlightLesson, content]);

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
      <div className={styles.page}>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>Не указан адрес курса.</p>
            <Button type="button" variant="outline" asChild>
              <Link to="/app/home">На главную</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (isError || !payload) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>
              Не удалось загрузить программу курса. Проверьте, что вы записаны на
              курс, и попробуйте снова.
            </p>
            <Button type="button" onClick={() => void refetch()}>
              Попробовать снова
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!content.length) {
    return (
      <PageTransition className={styles.page}>
        <div className={styles.breadcrumbWrap}>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link
                    to="/app/home"
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
          </aside>
        </div>
      </PageTransition>
    );
  }

  return (
    <PageTransition className={styles.page}>
      <div className={styles.breadcrumbWrap}>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link
                  to="/app/home"
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
              open={openSections.has(section.section_id)}
              onOpenChange={(o) => toggleSection(section.section_id, o)}
              highlightLessonSlug={highlightLesson}
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
                homeworkDone={8}
                homeworkTotal={11}
              />
            </>
          )}
        </aside>
      </div>
    </PageTransition>
  );
}

function SectionStaffTools({
  courseSlug,
  section,
  sectionSlug,
  canManageSection,
  editingTitle,
  onEditTitle,
  onDeleteSection,
  deletePending,
}: {
  courseSlug: string;
  section: AppCourseSection;
  sectionSlug: string;
  canManageSection: boolean;
  editingTitle: boolean;
  onEditTitle: () => void;
  onDeleteSection: () => void;
  deletePending: boolean;
}) {
  const toggleSectionType = useToggleSectionType(courseSlug);
  const published = section.type !== 'draft';

  return (
    <div
      className={styles.staffSectionTools}
      role="group"
      onClick={(e) => e.stopPropagation()}
    >
      {section.type !== undefined ? (
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={styles.publishBtn}
            disabled={!canManageSection || toggleSectionType.isPending}
            onClick={() => {
              if (!canManageSection) return;
              toggleSectionType.mutate({
                sectionSlug,
                currentType: section.type,
              });
            }}
          >
            {published ? 'Отозвать' : 'Опубликовать'}
          </Button>
          {published ? (
            <Eye size={20} className={styles.eyePublished} strokeWidth={2} />
          ) : (
            <EyeOff size={20} className={styles.eyeDraft} strokeWidth={2} />
          )}
        </>
      ) : null}
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        disabled={!canManageSection || editingTitle}
        title={
          canManageSection
            ? 'Редактировать название'
            : 'У раздела нет slug — обновите страницу или проверьте API'
        }
        onClick={onEditTitle}
      >
        <Pencil size={18} strokeWidth={2} />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        disabled={!canManageSection || deletePending}
        title={
          canManageSection
            ? 'Удалить раздел'
            : 'У раздела нет slug — обновите страницу или проверьте API'
        }
        onClick={onDeleteSection}
      >
        <Trash2 size={18} strokeWidth={2} />
      </Button>
    </div>
  );
}

function SectionBlock({
  section,
  courseSlug,
  isStaff,
  meta,
  open,
  onOpenChange,
  highlightLessonSlug,
}: {
  section: AppCourseSection;
  courseSlug: string;
  isStaff: boolean;
  meta: CourseHomeMeta;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  highlightLessonSlug: string | null;
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
    meta.completed_sections_id,
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
        `Раздел «${section.title}» и все его уроки будут удалены без возможности восстановления. Продолжить?`,
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
          date_time: new Date().toISOString(),
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
        <div className={styles.sectionHeader}>
          {isStaff ? (
            <span className={styles.dragHandle} aria-hidden>
              <GripVertical size={18} strokeWidth={2} />
            </span>
          ) : null}

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
                  !draftTitle.trim() || patchSection.isPending || !canManageSection
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
              courseSlug={courseSlug}
              section={section}
              sectionSlug={sectionSlug}
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
              {open ? (
                <ChevronUp size={22} strokeWidth={2} />
              ) : (
                <ChevronDown size={22} strokeWidth={2} />
              )}
            </button>
          </CollapsibleTrigger>
        </div>

        <CollapsibleContent>
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
                  meta.completed_lessons_id,
                )}
                highlighted={lesson.slug === highlightLessonSlug}
              />
            ))}

            {isStaff && addingLesson ? (
              <div className={styles.inlineAddLesson}>
                <Input
                  id={`new-lesson-input-${idKey(section.section_id)}`}
                  className={cn(
                    styles.inlineAddLessonInput,
                    styles.addFlowInputAnim,
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
                    styles.addFlowActionsAnim,
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
                  Добавить
                </button>
              </div>
            ) : null}
          </div>
        </CollapsibleContent>
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
  highlighted,
}: {
  lesson: AppCourseLesson;
  sectionNumber: number;
  courseSlug: string;
  isStaff: boolean;
  lessonDone: boolean;
  highlighted: boolean;
}) {
  const navigate = useNavigate();
  const toggleType = useToggleLessonType(courseSlug);
  const deleteLesson = useDeleteLesson(courseSlug);
  const lessonLabel = `${sectionNumber}.${lesson.lesson_number} ${lesson.title}`;
  const published = lesson.type !== 'draft';
  const lessonCreatePending = lesson.lesson_id.startsWith('optimistic:');

  const requestDeleteLesson = () => {
    if (
      !window.confirm(
        `Урок «${lesson.title}» будет удалён без возможности восстановления. Продолжить?`,
      )
    ) {
      return;
    }
    void deleteLesson.mutateAsync(lesson.slug);
  };

  if (isStaff) {
    return (
      <div
        className={cn(
          styles.lessonRow,
          styles.lessonRowStaff,
          highlighted && styles.lessonRowHighlight,
        )}
      >
        <span className={styles.dragHandleLesson} aria-hidden>
          <GripVertical size={16} strokeWidth={2} />
        </span>
        <span className={styles.lessonTitle}>{lessonLabel}</span>
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
          {published ? (
            <Eye size={20} className={styles.eyePublished} strokeWidth={2} />
          ) : (
            <EyeOff size={20} className={styles.eyeDraft} strokeWidth={2} />
          )}
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            disabled={lessonCreatePending}
            onClick={() =>
              navigate(
                `/app/courses/${courseSlug}/${encodeURIComponent(lesson.slug)}`,
              )
            }
          >
            <Pencil size={18} strokeWidth={2} />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            disabled={lessonCreatePending || deleteLesson.isPending}
            title="Удалить урок"
            onClick={requestDeleteLesson}
          >
            <Trash2 size={18} strokeWidth={2} />
          </Button>
        </div>
      </div>
    );
  }

  const to = `/app/courses/${courseSlug}/${encodeURIComponent(lesson.slug)}`;

  return (
    <Link
      to={to}
      className={cn(
        styles.lessonRow,
        styles.lessonRowStudent,
        highlighted && styles.lessonRowHighlight,
      )}
    >
      <span className={styles.lessonTitle}>{lessonLabel}</span>
      <StudentStatusIcon done={lessonDone} />
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
            className={styles.addSectionBtn}
            onClick={() => setExpanded(true)}
          >
            <Plus size={18} strokeWidth={2} />
            Добавить
          </Button>
        </div>
      ) : (
        <div className={styles.addSectionExpanded}>
          <Input
            id="new-section-input"
            className={cn(
              styles.inlineAddSectionInput,
              styles.addFlowInputAnim,
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
          <div
            className={cn(styles.addFlowActions, styles.addFlowActionsAnim)}
          >
            <Button
              type="button"
              variant="outline"
              className={styles.addSectionBtn}
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
              variant="outline"
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
