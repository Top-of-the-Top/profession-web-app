import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Home, Clock3, Video, CircleCheck } from 'lucide-react';
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
} from '@shared/ui';
import type { LessonLayout, Block } from '../../../features/course-builder';
import {
  FONT_SIZE_STEPS,
  DEFAULT_FONT_SIZE_INDEX,
} from '../../../features/course-builder/lib/constants';
import { parseLessonLayoutFromContentString } from '../../../features/course-builder/model/types';
import type { LessonHomework } from '@shared/api/courseApi';
import { useCourseHomeBySlug, useLessonBySlug } from '@shared/api/queries/courses';
import { useStartWebinar } from '@shared/api/mutations/webinar';
import { useToggleHomeworkType } from '@shared/api/mutations/courses';
import { useRole } from '@shared/lib/rbac';
import styles from './LessonViewPage.module.css';


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

function formatDeadline(iso: string): string {
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const HomeworkWidget: React.FC<{
  courseSlug: string;
  lessonSlug: string;
  homeworks: LessonHomework[];
  isTeacher: boolean;
}> = ({ courseSlug, lessonSlug, homeworks, isTeacher }) => {
  const toggleType = useToggleHomeworkType(courseSlug, lessonSlug);

  const visible = isTeacher
    ? homeworks
    : homeworks.filter((hw) => hw.type === 'published');

  if (visible.length === 0) {
    return (
      <div className={styles.sidebarCard}>
        <div className={styles.sidebarCardHeader}>
          <CircleCheck size={18} />
          <span className={styles.sidebarCardTitle}>Задание</span>
        </div>
        <div className={styles.noHomework}>Задание не назначено</div>
      </div>
    );
  }

  return (
    <div className={styles.sidebarCard}>
      <div className={styles.sidebarCardHeader}>
        <CircleCheck size={18} />
        <span className={styles.sidebarCardTitle}>
          {visible.length === 1 ? 'Задание' : 'Задания'}
        </span>
      </div>
      {visible.map((hw) => (
        <div key={hw.homework_id} className={styles.homeworkItem}>
          {isTeacher && (
            <div className={styles.homeworkStatusRow}>
              <span
                className={
                  hw.type === 'published'
                    ? styles.hwBadgePublished
                    : styles.hwBadgeDraft
                }
              >
                {hw.type === 'published' ? 'опубликовано' : 'черновик'}
              </span>
              <button
                type="button"
                className={styles.hwToggleButton}
                disabled={toggleType.isPending}
                onClick={() =>
                  toggleType.mutate({
                    homeworkSlug: hw.homework_slug,
                    currentType: hw.type,
                  })
                }
              >
                {hw.type === 'published' ? 'В черновик' : 'Опубликовать'}
              </button>
            </div>
          )}
          {hw.deadline && (
            <p className={styles.deadlineText}>
              Дедлайн: {formatDeadline(hw.deadline)}
            </p>
          )}
          <Link
            to={
              `/app/courses/${courseSlug}/${lessonSlug}/homework/${encodeURIComponent(hw.homework_slug)}`
            }
            className={styles.homeworkButton}
          >
            {hw.title || 'Перейти к заданию'}
          </Link>
        </div>
      ))}
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

const WebinarWidget: React.FC<{
  courseSlug: string;
  lessonSlug: string;
  isTeacher: boolean;
}> = ({ courseSlug, lessonSlug, isTeacher }) => {
  const navigate = useNavigate();
  const startWebinar = useStartWebinar(courseSlug, lessonSlug);

  const webinarUrl = `/app/courses/${courseSlug}/${lessonSlug}/webinar`;

  const handleStartWebinar = () => {
    startWebinar.mutate(undefined, {
      onSuccess: () => navigate(webinarUrl),
    });
  };

  const handleJoinWebinar = () => {
    navigate(webinarUrl);
  };

  return (
    <div className={styles.linksRow}>
      {isTeacher ? (
        <button
          type="button"
          className={styles.quickLinkButton}
          onClick={handleStartWebinar}
          disabled={startWebinar.isPending}
        >
          <Video size={20} />
          <span>{startWebinar.isPending ? 'Запуск...' : 'Начать вебинар'}</span>
        </button>
      ) : (
        <button
          type="button"
          className={styles.quickLinkButton}
          onClick={handleJoinWebinar}
        >
          <Video size={20} />
          <span>Подключиться к вебинару</span>
        </button>
      )}
    </div>
  );
};

const LessonEditWidget: React.FC<{
  courseSlug: string;
  lessonSlug: string;
}> = ({ courseSlug, lessonSlug }) => {
  return (
    <div className={styles.linksRow}>
      <Link
        to={`/app/courses/${courseSlug}/${lessonSlug}/edit`}
        className={styles.quickLinkButton}
      >
        Редактировать урок
      </Link>
    </div>
  );
};

const LessonRecording: React.FC<{ recording: string | null }> = ({ recording }) => {
  const value = recording?.trim();

  if (!value) return null;

  const isHttpLink = /^https?:\/\//i.test(value);

  return (
    <section className={styles.recordingSection}>
      <h2 className={styles.recordingTitle}>Запись урока</h2>
      {isHttpLink ? (
        <div className={styles.recordingIframeWrap}>
          <iframe
            src={value === "https://example.com/recordings/mock-lesson" ? "https://kinescope.io/t1go93i9aP3NG6VNPxiCC6" : value}
            allow="autoplay; fullscreen; picture-in-picture; encrypted-media; gyroscope; accelerometer; clipboard-write; screen-wake-lock;"
            allowFullScreen
            className={styles.recordingIframe}
            title="Запись урока"
          />
        </div>
      ) : (
        <div className={styles.mediaPlaceholder}>Запись урока недоступна</div>
      )}
    </section>
  );
};

/* ── Page ── */

export default function LessonViewPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const navigate = useNavigate();
  const { hasAny } = useRole();
  const isTeacher = hasAny('teacher', 'moderator');

  const homeQuery = useCourseHomeBySlug(courseSlug);
  const lessonQuery = useLessonBySlug(courseSlug, lessonSlug);

  const courseTitle =
    homeQuery.data?.title ??
    courseSlug?.replace(/-/g, ' ') ??
    'Курс';

  const lessonDetail = lessonQuery.data;

  const lessonLayout = useMemo<LessonLayout | null>(() => {
    if (!lessonDetail?.document) return null;
    try {
      return parseLessonLayoutFromContentString(lessonDetail.document);
    } catch {
      return {
        id: String(lessonDetail.lesson_id),
        title: lessonDetail.title,
        blocks: [],
      };
    }
  }, [lessonDetail]);

  const loading = lessonQuery.isLoading;
  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (lessonQuery.isError || !lessonDetail) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>
              Не удалось загрузить урок. Проверьте доступ и попробуйте снова.
            </p>
            <div className={styles.errorActions}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Назад
              </Button>
              <Button type="button" onClick={() => void lessonQuery.refetch()}>
                Попробовать снова
              </Button>
            </div>
          </div>
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
                <Link to={`/app/courses/${courseSlug}`}>
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
            <LessonRecording recording={lessonDetail.recording_url} />
            {lessonLayout && <LessonContent layout={lessonLayout} />}
          </main>
        </div>

        <aside className={styles.sidebar}>
          <TimerWidget targetIso={lessonDetail.started_at} />
          <WebinarWidget
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
            isTeacher={isTeacher}
          />
          {isTeacher && (
            <LessonEditWidget
              courseSlug={courseSlug ?? ''}
              lessonSlug={lessonSlug ?? ''}
            />
          )}
          <HomeworkWidget
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
            homeworks={lessonDetail.homeworks}
            isTeacher={isTeacher}
          />
          <ProgressWidget />
        </aside>
      </div>
    </PageTransition>
  );
}
