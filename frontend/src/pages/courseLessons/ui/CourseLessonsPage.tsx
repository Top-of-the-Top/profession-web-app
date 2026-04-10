import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom';
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
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
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Label,
  PageTransition,
  Spinner,
} from '@shared/ui';
import type {
  AppCourseLesson,
  AppCourseSection,
  CourseHomeMeta,
  CourseHomeResponse,
} from '@shared/api/courseApi';
import { useCourseHomeBySlug } from '@shared/api/queries/courses';
import {
  useCreateLesson,
  useDeleteLesson,
  useToggleLessonType,
} from '@shared/api/mutations/courses';
import { useRole } from '@shared/lib/rbac/useRole';
import { notifyInfo } from '@shared/lib/sileo/notify';
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

const MOCK_COURSE_HOME: CourseHomeResponse = {
  course_id: 'mock-course-id',
  title: 'Программирование (mock)',
  content: [
    {
      section_id: 'mock-section-1',
      section_number: 1,
      title: 'Введение',
      type: 'published',
      lessons: [
        {
          lesson_id: 'mock-lesson-id-1',
          lesson_number: 1,
          title: 'Первый урок',
          slug: 'mock-lesson-1',
          type: 'published',
        },
        {
          lesson_id: 'mock-lesson-id-2',
          lesson_number: 2,
          title: 'Второй урок',
          slug: 'mock-lesson-2',
          type: 'draft',
        },
      ],
    },
  ],
  meta: {
    completed_sections_id: ['mock-section-1'],
    completed_lessons_id: ['mock-lesson-id-1'],
  },
};

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

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();
  const highlightLesson = searchParams.get('lesson');
  const { hasAny } = useRole();
  const isStaff = hasAny('teacher', 'moderator');

  const homeQuery = useCourseHomeBySlug(slug);

  const payload: CourseHomeResponse = homeQuery.data ?? MOCK_COURSE_HOME;

  const title =
    (payload?.title && payload.title.trim() !== '' ? payload.title : null) ??
    slug?.replace(/-/g, ' ') ??
    'Курс';

  const loading = homeQuery.isLoading;

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

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <Spinner />
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
            {isStaff ? (
              <Button
                type="button"
                variant="outline"
                className={styles.addSectionBtn}
                onClick={() => notifyInfo({ title: 'В разработке' })}
              >
                <Plus size={18} strokeWidth={2} />
                Добавить раздел
              </Button>
            ) : null}
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

          {isStaff ? (
            <Button
              type="button"
              variant="outline"
              className={styles.addSectionBtn}
              onClick={() => notifyInfo({ title: 'В разработке' })}
            >
              <Plus size={18} strokeWidth={2} />
              Добавить раздел
            </Button>
          ) : null}
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
  const sectionDone = isSectionCompleted(
    section.section_id,
    meta.completed_sections_id,
  );

  const stubAction = () => notifyInfo({ title: 'В разработке' });

  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <div className={styles.sectionCard}>
        <div className={styles.sectionHeader}>
          {isStaff ? (
            <span className={styles.dragHandle} aria-hidden>
              <GripVertical size={18} strokeWidth={2} />
            </span>
          ) : null}

          <CollapsibleTrigger asChild>
            <button type="button" className={styles.sectionTitleBtn}>
              <span className={styles.sectionTitleText}>
                {section.section_number}. {section.title}
              </span>
            </button>
          </CollapsibleTrigger>

          {isStaff ? (
            <div
              className={styles.staffSectionTools}
              role="group"
              onClick={(e) => e.stopPropagation()}
            >
              <Button type="button" variant="ghost" size="icon-sm" onClick={stubAction}>
                <Pencil size={18} strokeWidth={2} />
              </Button>
              <Button type="button" variant="ghost" size="icon-sm" onClick={stubAction}>
                <Trash2 size={18} strokeWidth={2} />
              </Button>
            </div>
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

            {isStaff ? (
              <AddLessonDialog
                courseSlug={courseSlug}
                sectionId={section.section_id}
              />
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
  const lessonLabel = `${sectionNumber}.${lesson.lesson_number} ${lesson.title}`;
  const published = lesson.type !== 'draft';
  const [deleteOpen, setDeleteOpen] = useState(false);

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
            disabled={toggleType.isPending}
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
            onClick={() =>
              navigate(
                `/app/courses/${courseSlug}/lessons/${encodeURIComponent(lesson.slug)}`,
              )
            }
          >
            <Pencil size={18} strokeWidth={2} />
          </Button>
          <DeleteLessonDialog
            courseSlug={courseSlug}
            lessonSlug={lesson.slug}
            lessonTitle={lesson.title}
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
          />
        </div>
      </div>
    );
  }

  const to = `/app/courses/${courseSlug}/lessons/${encodeURIComponent(lesson.slug)}`;

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

function DeleteLessonDialog({
  courseSlug,
  lessonSlug,
  lessonTitle,
  open,
  onOpenChange,
}: {
  courseSlug: string;
  lessonSlug: string;
  lessonTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const deleteMutation = useDeleteLesson(courseSlug);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogTrigger asChild>
        <Button type="button" variant="ghost" size="icon-sm">
          <Trash2 size={18} strokeWidth={2} />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Удалить урок?</AlertDialogTitle>
          <AlertDialogDescription>
            Урок «{lessonTitle}» будет удалён без возможности восстановления.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Отмена</AlertDialogCancel>
          <AlertDialogAction
            disabled={deleteMutation.isPending}
            onClick={() =>
              deleteMutation.mutate(lessonSlug, {
                onSuccess: () => onOpenChange(false),
              })
            }
          >
            {deleteMutation.isPending ? 'Удаление…' : 'Удалить'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function AddLessonDialog({
  courseSlug,
  sectionId,
}: {
  courseSlug: string;
  sectionId: string;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const createMutation = useCreateLesson(courseSlug);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) return;
    createMutation.mutate(
      { title: trimmed, section: sectionId },
      {
        onSuccess: () => {
          setTitle('');
          setOpen(false);
        },
      },
    );
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setTitle('');
      }}
    >
      <DialogTrigger asChild>
        <button type="button" className={styles.addLessonZone}>
          <Plus size={18} strokeWidth={2} />
          Добавить урок
        </button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Новый урок</DialogTitle>
          </DialogHeader>
          <div style={{ padding: '16px 0' }}>
            <Label htmlFor="new-lesson-title">Название урока</Label>
            <Input
              id="new-lesson-title"
              ref={inputRef}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Введите название"
              autoFocus
              disabled={createMutation.isPending}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Отмена
              </Button>
            </DialogClose>
            <Button
              type="submit"
              disabled={!title.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? <Spinner /> : 'Создать'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
