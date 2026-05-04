import { useMemo, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Home } from 'lucide-react';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  PageFrame,
  Spinner,
} from '@shared/ui';
import type {
  HomeworkAttemptStatus,
} from '@shared/api/courseApi';
import { courseApi } from '@shared/api/courseApi';
import { courseKeys, useCourseHomeBySlug } from '@shared/api/queries/courses';
import { useRole } from '@shared/lib/rbac/useRole';
import { cn } from '@shared/lib/utils';
import { AiChatPanel } from '../../../features/ai-chat';
import { AddSectionRow } from './components/AddSectionRow';
import { SectionBlock } from './components/SectionBlock';
import styles from './CourseLessonsPage.module.css';

function idKey(id: number | string): string {
  return String(id);
}

function isLessonCompleted(lessonId: string, completed: string[]): boolean {
  const key = idKey(lessonId);
  return completed.some((c) => String(c) === key);
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
