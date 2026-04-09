import { useEffect, useMemo, useState } from 'react';
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
  PageTransition,
  Spinner,
} from '@shared/ui';
import type {
  AppCourseLesson,
  AppCourseSection,
  AppCourseContentResponse,
} from '@shared/api/courseApi';
import { useAppCourseBySlug, useCourseBySlug } from '@shared/api/queries/courses';
import { useRole } from '@shared/lib/rbac/useRole';
import { cn } from '@shared/lib/utils';
import styles from './CourseLessonsPage.module.css';
import {
  USE_MOCK,
  MOCK_APP_COURSE,
  MOCK_COURSE_PAGE_TITLE,
} from './mockCourseLessonsData';

function idKey(id: number | string): string {
  return String(id);
}

function isLessonCompleted(
  lessonId: number | string,
  completed: number[],
): boolean {
  const key = idKey(lessonId);
  return completed.some((c) => String(c) === key);
}

function isSectionCompleted(sectionId: number, completed: number[]): boolean {
  return completed.includes(sectionId);
}

function findSectionIdForLessonSlug(
  sections: AppCourseSection[],
  lessonSlug: string | null,
): number | null {
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

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const highlightLesson = searchParams.get('lesson');
  const { hasAny } = useRole();
  const isStaff = hasAny('teacher', 'moderator');

  const appQuery = useAppCourseBySlug(USE_MOCK ? undefined : slug);
  const catalogQuery = useCourseBySlug(USE_MOCK ? undefined : slug);

  const payload: AppCourseContentResponse | undefined = USE_MOCK
    ? MOCK_APP_COURSE
    : appQuery.data;

  const title = USE_MOCK
    ? MOCK_COURSE_PAGE_TITLE
    : (catalogQuery.data?.title ??
      slug?.replace(/-/g, ' ') ??
      'Курс');

  const loading = !USE_MOCK && appQuery.isLoading;
  const error = !USE_MOCK && appQuery.error;

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

  const [openSections, setOpenSections] = useState<Set<number>>(
    () => (USE_MOCK ? new Set([3, 4]) : new Set()),
  );

  useEffect(() => {
    if (!highlightLesson || !content.length) return;
    const sid = findSectionIdForLessonSlug(content, highlightLesson);
    if (sid != null) {
      setOpenSections((prev) => new Set(prev).add(sid));
    }
  }, [highlightLesson, content]);

  const toggleSection = (sectionId: number, open: boolean) => {
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

  if (error || (!USE_MOCK && !appQuery.data)) {
    return (
      <div className={styles.page}>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>
            {error ? 'Не удалось загрузить курс' : 'Курс недоступен'}
          </p>
          <Button variant="secondary" onClick={() => navigate('/app/home')}>
            К курсам
          </Button>
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
        <div className={styles.empty}>В этом курсе пока нет разделов.</div>
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
              slug={slug ?? ''}
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
  slug,
  isStaff,
  meta,
  open,
  onOpenChange,
  highlightLessonSlug,
}: {
  section: AppCourseSection;
  slug: string;
  isStaff: boolean;
  meta: AppCourseContentResponse['meta'];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  highlightLessonSlug: string | null;
}) {
  const sectionDone = isSectionCompleted(
    section.section_id,
    meta.completed_sections_id,
  );

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
              <Button type="button" variant="ghost" size="icon-sm">
                <Pencil size={18} strokeWidth={2} />
              </Button>
              <Button type="button" variant="ghost" size="icon-sm">
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
                slug={slug}
                isStaff={isStaff}
                lessonDone={isLessonCompleted(
                  lesson.lesson_id,
                  meta.completed_lessons_id,
                )}
                highlighted={lesson.slug === highlightLessonSlug}
              />
            ))}

            {isStaff ? (
              <button type="button" className={styles.addLessonZone}>
                <Plus size={18} strokeWidth={2} />
                Добавить урок
              </button>
            ) : null}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

function LessonRow({
  lesson,
  slug,
  isStaff,
  lessonDone,
  highlighted,
}: {
  lesson: AppCourseLesson;
  slug: string;
  isStaff: boolean;
  lessonDone: boolean;
  highlighted: boolean;
}) {
  const published = lesson.type !== 'draft';

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
        <span className={styles.lessonTitle}>
          {lesson.lesson_number} {lesson.title}
        </span>
        <div className={styles.staffLessonActions}>
          <Button type="button" variant="outline" size="sm" className={styles.publishBtn}>
            {published ? 'Отозвать' : 'Опубликовать'}
          </Button>
          {published ? (
            <Eye size={20} className={styles.eyePublished} strokeWidth={2} />
          ) : (
            <EyeOff size={20} className={styles.eyeDraft} strokeWidth={2} />
          )}
          <Button type="button" variant="ghost" size="icon-sm">
            <Pencil size={18} strokeWidth={2} />
          </Button>
          <Button type="button" variant="ghost" size="icon-sm">
            <Trash2 size={18} strokeWidth={2} />
          </Button>
        </div>
      </div>
    );
  }

  const to = `/app/courses/${slug}/lessons/${encodeURIComponent(lesson.slug)}`;

  return (
    <Link
      to={to}
      className={cn(
        styles.lessonRow,
        styles.lessonRowStudent,
        highlighted && styles.lessonRowHighlight,
      )}
    >
      <span className={styles.lessonTitle}>
        {lesson.lesson_number} {lesson.title}
      </span>
      <StudentStatusIcon done={lessonDone} />
    </Link>
  );
}
