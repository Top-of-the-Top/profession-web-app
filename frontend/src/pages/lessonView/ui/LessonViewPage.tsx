import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Home, Clock3, PenTool, Video, CircleCheck } from 'lucide-react';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  PageTransition,
  Spinner,
} from '../../../shared/ui';
import type { LessonLayout, Block } from '../../../features/course-builder';
import {
  FONT_SIZE_STEPS,
  DEFAULT_FONT_SIZE_INDEX,
} from '../../../features/course-builder/lib/constants';
import { parseLessonLayout } from '../../../features/course-builder/model/types';
import { useCourseBySlug, useLessonBySlug } from '../../../shared/api/queries/courses';
import { USE_MOCK, MOCK_LESSON, MOCK_COURSE_TITLE } from './mockLessonData';
import styles from './LessonViewPage.module.css';

/* ── Block views (read-only, reused from CourseRenderer logic) ── */

const TextBlockView: React.FC<{ html: string; fontSizeIndex?: number }> = ({
  html,
  fontSizeIndex,
}) => {
  const fontSize =
    FONT_SIZE_STEPS[fontSizeIndex ?? DEFAULT_FONT_SIZE_INDEX] ??
    FONT_SIZE_STEPS[DEFAULT_FONT_SIZE_INDEX];

  return (
    <div
      className={styles.textBlock}
      style={{ fontSize }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

const PhotoBlockView: React.FC<{ url: string }> = ({ url }) => {
  if (!url)
    return <div className={styles.mediaPlaceholder}>Изображение не загружено</div>;
  return (
    <div className={styles.photoBlock}>
      <img src={url} alt="" loading="lazy" />
    </div>
  );
};

const VideoBlockView: React.FC<{ url: string }> = ({ url }) => {
  if (!url)
    return <div className={styles.mediaPlaceholder}>Видео не загружено</div>;
  return (
    <div className={styles.videoBlock}>
      <video src={url} controls playsInline />
    </div>
  );
};

function renderBlock(block: Block) {
  switch (block.type) {
    case 'text':
      return <TextBlockView html={block.html} fontSizeIndex={block.fontSizeIndex} />;
    case 'photo':
      return <PhotoBlockView url={block.url} />;
    case 'video':
      return <VideoBlockView url={block.url} />;
    default:
      return null;
  }
}

/* ── Content grid ── */

const LessonContent: React.FC<{ layout: LessonLayout }> = ({ layout }) => {
  const maxRow = layout.blocks.reduce((acc, b) => Math.max(acc, b.y + b.h), 0);

  if (layout.blocks.length === 0) {
    return <div className={styles.emptyContent}>Контент урока пуст</div>;
  }

  return (
    <div
      className={styles.blockGrid}
      style={{ gridTemplateRows: `repeat(${maxRow}, minmax(60px, auto))` }}
    >
      {layout.blocks.map((block) => (
        <div
          key={block.id}
          className={styles.blockCell}
          style={{
            gridColumn: `${block.x + 1} / span ${block.w}`,
            gridRow: `${block.y + 1} / span ${block.h}`,
          }}
        >
          {renderBlock(block)}
        </div>
      ))}
    </div>
  );
};

/* ── Sidebar widgets ── */

const HomeworkWidget: React.FC<{
  courseSlug: string;
  lessonSlug: string;
  homeworkSlug: string | null;
  deadline: string | null;
}> = ({ courseSlug, lessonSlug, homeworkSlug, deadline }) => {
  const formattedDeadline = deadline
    ? (() => {
        try {
          return new Intl.DateTimeFormat('ru-RU', {
            day: 'numeric',
            month: 'long',
            hour: '2-digit',
            minute: '2-digit',
          }).format(new Date(deadline));
        } catch {
          return deadline;
        }
      })()
    : null;

  return (
    <div className={styles.sidebarCard}>
      <div className={styles.sidebarCardHeader}>
        <CircleCheck size={18} />
        <span className={styles.sidebarCardTitle}>Задание</span>
      </div>
      {formattedDeadline && (
        <p className={styles.deadlineText}>Дедлайн: {formattedDeadline}</p>
      )}
      {homeworkSlug ? (
        <Link
          to={`/app/courses/${courseSlug}/lessons/${lessonSlug}/homework/${homeworkSlug}`}
          className={styles.homeworkButton}
        >
          Перейти к заданию
        </Link>
      ) : (
        <div className={styles.noHomework}>Задание не назначено</div>
      )}
    </div>
  );
};

const ProgressWidget: React.FC = () => {
  const passedLessons = { done: 12, total: 24 };
  const submittedHomeworks = { done: 8, total: 11 };

  const passedPct = Math.round((passedLessons.done / passedLessons.total) * 100);
  const submittedPct = Math.round(
    (submittedHomeworks.done / submittedHomeworks.total) * 100,
  );

  return (
    <div className={styles.sidebarCard}>
      <div className={styles.sidebarCardHeader}>
        <span className={styles.progressRoundIcon}></span>
        <span className={styles.sidebarCardTitle}>Ваш прогресс</span>
      </div>

      <div className={styles.progressSection}>
        <div className={styles.progressHeaderRow}>
          <span className={styles.progressHeaderLabel}>Пройдено уроков</span>
          <span className={styles.progressHeaderValue}>
            {passedLessons.done}/{passedLessons.total}
          </span>
        </div>
        <div className={styles.progressBarTrack}>
          <div
            className={styles.progressBarFill}
            style={{ width: `${passedPct}%` }}
          />
        </div>
      </div>

      <div className={styles.progressSection}>
        <div className={styles.progressHeaderRow}>
          <span className={styles.progressHeaderLabel}>Сдано заданий</span>
          <span className={styles.progressHeaderValue}>
            {submittedHomeworks.done}/{submittedHomeworks.total}
          </span>
        </div>
        <div className={styles.progressBarTrack}>
          <div
            className={styles.progressBarFill}
            style={{ width: `${submittedPct}%` }}
          />
        </div>
      </div>
    </div>
  );
};

type TimerState = {
  days: string;
  hours: string;
  minutes: string;
  seconds: string;
};

function getTimerState(targetIso: string | null): TimerState {
  if (!targetIso) {
    return { days: '00', hours: '00', minutes: '00', seconds: '00' };
  }

  const targetMs = new Date(targetIso).getTime();
  if (!Number.isFinite(targetMs)) {
    return { days: '00', hours: '00', minutes: '00', seconds: '00' };
  }

  const delta = Math.max(0, targetMs - Date.now());
  const totalSeconds = Math.floor(delta / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return {
    days: String(days).padStart(2, '0'),
    hours: String(hours).padStart(2, '0'),
    minutes: String(minutes).padStart(2, '0'),
    seconds: String(seconds).padStart(2, '0'),
  };
}

const TimerWidget: React.FC<{ targetIso: string | null }> = ({ targetIso }) => {
  const [timer, setTimer] = useState<TimerState>(() => getTimerState(targetIso));

  useEffect(() => {
    setTimer(getTimerState(targetIso));
    const intervalId = window.setInterval(() => {
      setTimer(getTimerState(targetIso));
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [targetIso]);

  return (
    <div className={styles.timerCard}>
      <div className={styles.sidebarCardHeader}>
        <Clock3 size={18} />
        <span className={styles.sidebarCardTitle}>До начала вебинара</span>
      </div>
      <div className={styles.timerGrid}>
        <div className={styles.timerCol}>
          <div className={styles.timerCell}>
            <span className={styles.timerValue}>{timer.days}</span>
          </div>
          <span className={styles.timerLabel}>дни</span>
        </div>
        <div className={styles.timerCol}>
          <div className={styles.timerCell}>
            <span className={styles.timerValue}>{timer.hours}</span>
          </div>
          <span className={styles.timerLabel}>часы</span>
        </div>
        <div className={styles.timerCol}>
          <div className={styles.timerCell}>
            <span className={styles.timerValue}>{timer.minutes}</span>
          </div>
          <span className={styles.timerLabel}>мин</span>
        </div>
        <div className={styles.timerCol}>
          <div className={styles.timerCell}>
            <span className={styles.timerValue}>{timer.seconds}</span>
          </div>
          <span className={styles.timerLabel}>сек</span>
        </div>
      </div>
    </div>
  );
};

const WebinarLinksWidget: React.FC<{
  boardUrl: string | null;
  webinarUrl: string | null;
}> = ({ boardUrl, webinarUrl }) => (
  <div className={styles.linksRow}>
    <a
      href={boardUrl ?? '#'}
      target="_blank"
      rel="noreferrer"
      className={`${styles.quickLinkButton} ${!boardUrl ? styles.quickLinkDisabled : ''}`}
      aria-disabled={!boardUrl}
      onClick={(e) => {
        if (!boardUrl) e.preventDefault();
      }}
    >
      <PenTool size={20} />
      <span>Доска</span>
    </a>
    <a
      href={webinarUrl ?? '#'}
      target="_blank"
      rel="noreferrer"
      className={`${styles.quickLinkButton} ${!webinarUrl ? styles.quickLinkDisabled : ''}`}
      aria-disabled={!webinarUrl}
      onClick={(e) => {
        if (!webinarUrl) e.preventDefault();
      }}
    >
      <Video size={20} />
      <span>Вебинар</span>
    </a>
  </div>
);

/* ── Page ── */

export default function LessonViewPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const navigate = useNavigate();

  const courseQuery = useCourseBySlug(
    USE_MOCK ? undefined : courseSlug,
  );
  const lessonQuery = useLessonBySlug(
    USE_MOCK ? undefined : courseSlug,
    USE_MOCK ? undefined : lessonSlug,
  );

  const courseTitle = USE_MOCK
    ? MOCK_COURSE_TITLE
    : (courseQuery.data?.course.title ?? null);

  const lessonDetail = USE_MOCK ? MOCK_LESSON : (lessonQuery.data ?? null);

  const lessonLayout = useMemo<LessonLayout | null>(() => {
    if (!lessonDetail) return null;
    try {
      return parseLessonLayout(lessonDetail.content);
    } catch {
      return {
        id: String(lessonDetail.lesson_id),
        title: lessonDetail.title,
        blocks: [],
      };
    }
  }, [lessonDetail]);

  const loading = !USE_MOCK && (courseQuery.isLoading || lessonQuery.isLoading);
  const error = courseQuery.error || lessonQuery.error;

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (error || !courseTitle || !lessonDetail) {
    return (
      <div className={styles.page}>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>
            {error ? 'Не удалось загрузить урок' : 'Урок недоступен'}
          </p>
          <Button variant="secondary" onClick={() => navigate(-1)}>
            Назад
          </Button>
        </div>
      </div>
    );
  }

  return (
    <PageTransition className={styles.page}>
      <div className={styles.breadcrumbWrap}>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to="/app/home" className={styles.homeLink} aria-label="Домашняя">
                  <Home size={18} strokeWidth={2} />
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to={`/app/courses/${courseSlug}/lessons`}>
                  {courseTitle}
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{lessonDetail.title}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <div className={styles.lessonHeader}>
            <div className={styles.lessonHeaderTrapezoid}>
              <h1 className={styles.lessonTitleTrapezoid}>{lessonDetail.title}</h1>
            </div>
          </div>

          <main className={styles.main}>
            {lessonLayout && <LessonContent layout={lessonLayout} />}
          </main>
        </div>

        <aside className={styles.sidebar}>
          <TimerWidget targetIso={lessonDetail.date} />
          <WebinarLinksWidget
            boardUrl={lessonDetail.board_url}
            webinarUrl={lessonDetail.webinar_url}
          />
          <HomeworkWidget
            courseSlug={courseSlug ?? 'mock-course'}
            lessonSlug={lessonSlug ?? lessonDetail.slug}
            homeworkSlug={lessonDetail.homework_slug}
            deadline={lessonDetail.homework_deadline}
          />
          <ProgressWidget />
        </aside>
      </div>
    </PageTransition>
  );
}
