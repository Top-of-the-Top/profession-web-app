import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Home, Clock3, Video, CircleCheck, FileDown, Trash2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  PageFrame,
  SafeHtml,
  Spinner,
} from '@shared/ui';
import type { LessonLayout, Block } from '../../../features/course-builder';
import {
  FONT_SIZE_STEPS,
  DEFAULT_FONT_SIZE_INDEX,
} from '../../../features/course-builder/lib/constants';
import { parseLessonLayoutFromContentString } from '../../../features/course-builder/model/types';
import type {
  LessonMeta,
  LessonMetaStaff,
  LessonMetaStudent,
  LessonRecording,
  LessonHomework,
  WebinarStatus,
} from '@shared/api/courseApi';
import { useLessonBySlug } from '@shared/api/queries/courses';
import { connectWebinarSSE } from '../../../features/webinar';
import {
  useDeleteRecording,
  useDeleteRecordingPdf,
  useStartWebinar,
} from '@shared/api/mutations/webinar';
import { useToggleHomeworkType, useScheduleWebinar } from '@shared/api/mutations/courses';
import { useRole } from '@shared/lib/rbac';
import { homeworkReviewNavigateState } from '@shared/lib/homeworkReviewNavigation';
import { cn } from '@shared/lib/utils';
import { AiChatPanel } from '../../../features/ai-chat';
import { preloadWebinarRoute } from '@router/lazyPages';
import styles from './LessonViewPage.module.css';
import { useRecordingHeartbeat } from './hooks/useRecordingHeartbeat';

const TextBlockView: React.FC<{ html: string; fontSizeIndex?: number }> = ({
  html,
  fontSizeIndex,
}) => {
  const fontSize =
    FONT_SIZE_STEPS[fontSizeIndex ?? DEFAULT_FONT_SIZE_INDEX] ??
    FONT_SIZE_STEPS[DEFAULT_FONT_SIZE_INDEX];

  return (
    <SafeHtml className={styles.textBlock} style={{ fontSize }} html={html} />
  );
};

const PhotoBlockView: React.FC<{ url: string }> = ({ url }) => {
  if (!url)
    return (
      <div className={styles.mediaPlaceholder}>Изображение не загружено</div>
    );
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
      return (
        <TextBlockView html={block.html} fontSizeIndex={block.fontSizeIndex} />
      );
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
      {visible.map((hw, index) => {
        const status = hw.attempt_status;
        const actionLabel = status === 'reviewed'
          ? 'Посмотреть результат'
          : status === 'submitted'
            ? 'Посмотреть отправку'
            : 'Сдать ДЗ';
        return (
          <div
            key={hw.homework_id}
            className={cn(
              styles.homeworkItem,
              index > 0 && styles.homeworkItemDivided,
            )}
          >
            <p className={styles.homeworkItemTitle}>
              {hw.title || `ДЗ #${index + 1}`}
            </p>
            {!isTeacher && (
              <div className={styles.homeworkStatusRow}>
                <span
                  className={
                    status === 'reviewed'
                      ? styles.hwBadgePublished
                      : status === 'submitted'
                        ? styles.hwBadgeDraft
                        : styles.hwBadgePending
                  }
                >
                  {status === 'reviewed'
                    ? 'проверено'
                    : status === 'submitted'
                      ? 'отправлено'
                      : 'не сдано'}
                </span>
              </div>
            )}
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
            {!isTeacher && (
              <Link
                to={`/app/courses/${courseSlug}/${lessonSlug}/homework/${encodeURIComponent(hw.homework_slug)}`}
                className={styles.homeworkButton}
              >
                {actionLabel}
              </Link>
            )}
          </div>
        );
      })}
      <Link
        to={`/app/homeworks?course_slug=${courseSlug}&lesson_slug=${lessonSlug}`}
        className={styles.homeworkButton}
        style={{ marginTop: 8, opacity: 0.7, fontSize: '0.8rem' }}
      >
        Все ДЗ урока
      </Link>
    </div>
  );
};

const ProgressWidget: React.FC<{ meta: LessonMeta }> = ({ meta }) => {
  if (meta.role === 'student') {
    const m = meta as LessonMetaStudent;
    const watchedPct = Math.round(m.watched_ratio * 100);
    const hwPct = m.homeworks_total > 0
      ? Math.round((m.homeworks_submitted / m.homeworks_total) * 100)
      : 0;
    return (
      <div className={styles.sidebarCard}>
        <div className={styles.sidebarCardHeader}>
          <span className={styles.progressRoundIcon}></span>
          <span className={styles.sidebarCardTitle}>Ваш прогресс</span>
        </div>
        {m.is_completed && (
          <div className={styles.lessonCompletedBadge}>
            <CircleCheck size={14} />
            Урок пройден
          </div>
        )}
        <div className={styles.progressSection}>
          <div className={styles.progressHeaderRow}>
            <span className={styles.progressHeaderLabel}>Вебинар</span>
            <span className={styles.progressHeaderValue}>{watchedPct}%</span>
          </div>
          <div className={styles.progressBarTrack}>
            <div className={styles.progressBarFill} style={{ width: `${watchedPct}%` }} />
          </div>
        </div>
        <div className={styles.progressSection}>
          <div className={styles.progressHeaderRow}>
            <span className={styles.progressHeaderLabel}>ДЗ</span>
            <span className={styles.progressHeaderValue}>
              {m.homeworks_submitted}/{m.homeworks_total}
            </span>
          </div>
          <div className={styles.progressBarTrack}>
            <div className={styles.progressBarFill} style={{ width: `${hwPct}%` }} />
          </div>
        </div>
      </div>
    );
  }

  if (meta.role === 'teacher_or_moderator') {
    const m = meta as LessonMetaStaff;
    const attendedPct = m.attended_total > 0
      ? Math.round((m.attended_count / m.attended_total) * 100)
      : 0;
    const hwPct = m.homework_submitted_total > 0
      ? Math.round((m.homework_submitted_count / m.homework_submitted_total) * 100)
      : 0;
    return (
      <div className={styles.sidebarCard}>
        <div className={styles.sidebarCardHeader}>
          <span className={styles.progressRoundIcon}></span>
          <span className={styles.sidebarCardTitle}>Статистика урока</span>
        </div>
        <div className={styles.progressSection}>
          <div className={styles.progressHeaderRow}>
            <span className={styles.progressHeaderLabel}>На вебинаре было</span>
            <span className={styles.progressHeaderValue}>
              {m.attended_count}/{m.attended_total}
            </span>
          </div>
          <div className={styles.progressBarTrack}>
            <div className={styles.progressBarFill} style={{ width: `${attendedPct}%` }} />
          </div>
        </div>
        <div className={styles.progressSection}>
          <div className={styles.progressHeaderRow}>
            <span className={styles.progressHeaderLabel}>ДЗ сдали</span>
            <span className={styles.progressHeaderValue}>
              {m.homework_submitted_count}/{m.homework_submitted_total}
            </span>
          </div>
          <div className={styles.progressBarTrack}>
            <div className={styles.progressBarFill} style={{ width: `${hwPct}%` }} />
          </div>
        </div>
      </div>
    );
  }

  return null;
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
  const [timer, setTimer] = useState<TimerState>(() =>
    getTimerState(targetIso)
  );

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
  webinarStatus: WebinarStatus | null;
}> = ({ courseSlug, lessonSlug, isTeacher, webinarStatus }) => {
  const navigate = useNavigate();
  const startWebinar = useStartWebinar(courseSlug, lessonSlug);
  const [isJoiningWebinar, setIsJoiningWebinar] = useState(false);

  const webinarUrl = `/app/courses/${courseSlug}/${lessonSlug}/webinar`;

  const handleStartWebinar = () => {
    startWebinar.mutate(undefined, {
      onSuccess: async () => {
        setIsJoiningWebinar(true);
        await preloadWebinarRoute();
        navigate(webinarUrl);
      },
      onSettled: () => {
        setIsJoiningWebinar(false);
      },
    });
  };

  const handleJoinLive = async () => {
    setIsJoiningWebinar(true);
    await preloadWebinarRoute();
    navigate(webinarUrl);
  };

  if (webinarStatus === 'live') {
    return (
      <div className={styles.linksRow}>
        <button
          type="button"
          className={styles.quickLinkButton}
          onPointerEnter={() => {
            void preloadWebinarRoute();
          }}
          onFocus={() => {
            void preloadWebinarRoute();
          }}
          onClick={() => {
            void handleJoinLive();
          }}
          disabled={isJoiningWebinar}
        >
          <Video size={20} />
          <span>
            {isJoiningWebinar
              ? 'Переход...'
              : isTeacher
                ? 'Вернуться в звонок'
                : 'Войти в вебинар'}
          </span>
        </button>
      </div>
    );
  }

  if (!isTeacher) {
    return null;
  }

  return (
    <div className={styles.linksRow}>
      <button
        type="button"
        className={styles.quickLinkButton}
        onPointerEnter={() => {
          void preloadWebinarRoute();
        }}
        onFocus={() => {
          void preloadWebinarRoute();
        }}
        onClick={handleStartWebinar}
        disabled={startWebinar.isPending || isJoiningWebinar}
      >
        <Video size={20} />
        <span>
          {startWebinar.isPending
            ? 'Запуск...'
            : isJoiningWebinar
              ? 'Переход...'
              : 'Начать вебинар'}
        </span>
      </button>
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

function toLocalDatetimeValue(iso: string | null): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (!Number.isFinite(d.getTime())) return '';
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return '';
  }
}

const WebinarScheduleWidget: React.FC<{
  courseSlug: string;
  lessonSlug: string;
  scheduledAt: string | null;
}> = ({ courseSlug, lessonSlug, scheduledAt }) => {
  const schedule = useScheduleWebinar(courseSlug, lessonSlug);
  const [modalOpen, setModalOpen] = useState(false);
  const [value, setValue] = useState('');

  const openModal = () => {
    setValue(toLocalDatetimeValue(scheduledAt));
    setModalOpen(true);
  };

  const handleSave = () => {
    if (!value) return;
    schedule.mutate(new Date(value).toISOString(), {
      onSuccess: () => setModalOpen(false),
    });
  };

  const handleClear = () => {
    schedule.mutate(null);
  };

  return (
    <>
      <div className={styles.sidebarCard}>
        <div className={styles.sidebarCardHeader}>
          <Clock3 size={18} />
          <span className={styles.sidebarCardTitle}>Время вебинара</span>
        </div>
        <div className={styles.scheduleActions}>
          <button type="button" className={styles.scheduleBtn} onClick={openModal}>
            {scheduledAt ? 'Изменить время' : 'Назначить вебинар'}
          </button>
          {scheduledAt && (
            <button
              type="button"
              className={styles.scheduleBtnClear}
              disabled={schedule.isPending}
              onClick={handleClear}
            >
              Снять расписание
            </button>
          )}
        </div>
      </div>

      {modalOpen && (
        <div className={styles.scheduleOverlay} onClick={() => setModalOpen(false)}>
          <div className={styles.scheduleModal} onClick={(e) => e.stopPropagation()}>
            <p className={styles.scheduleModalTitle}>
              {scheduledAt ? 'Изменить время вебинара' : 'Назначить вебинар'}
            </p>
            <input
              type="datetime-local"
              className={styles.scheduleInput}
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
            <div className={styles.scheduleModalActions}>
              <button
                type="button"
                className={styles.scheduleBtnClear}
                onClick={() => setModalOpen(false)}
              >
                Отмена
              </button>
              <button
                type="button"
                className={styles.scheduleBtn}
                disabled={schedule.isPending || !value}
                onClick={handleSave}
              >
                {schedule.isPending ? 'Сохранение…' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

type RecordingDeleteConfirm =
  | null
  | { kind: 'recording'; recordingId: string; dateLabel: string }
  | { kind: 'pdf'; recordingId: string; dateLabel: string };

const LessonRecordingCard: React.FC<{
  recording: LessonRecording;
  isTeacher: boolean;
  onRequestDeletePdf: (payload: { recordingId: string; dateLabel: string }) => void;
  onRequestDeleteRecording: (payload: {
    recordingId: string;
    dateLabel: string;
  }) => void;
  deletePdfPending: boolean;
  deleteRecordingPending: boolean;
  isLeaving?: boolean;
  onLeavingRemoveComplete?: () => void;
}> = ({
  recording,
  isTeacher,
  onRequestDeletePdf,
  onRequestDeleteRecording,
  deletePdfPending,
  deleteRecordingPending,
  isLeaving,
  onLeavingRemoveComplete,
}) => {
  const leaveExitDoneRef = useRef(false);
  const kinescopeContainerRef = useRef<HTMLDivElement>(null);

  const incomingEmbedUrl =
    recording.kind !== 'whiteboard_only' && recording.kinescope_embed_url
      ? recording.kinescope_embed_url
      : null;
  const [stableEmbedUrl, setStableEmbedUrl] = useState<string | null>(incomingEmbedUrl);
  useEffect(() => {
    if (incomingEmbedUrl) {
      setStableEmbedUrl(incomingEmbedUrl);
    }
  }, [incomingEmbedUrl]);

  useRecordingHeartbeat({
    recordingId: recording.recording_id || null,
    embedUrl: stableEmbedUrl,
    containerRef: kinescopeContainerRef,
  });

  useEffect(() => {
    if (!isLeaving || !onLeavingRemoveComplete) {
      leaveExitDoneRef.current = false;
      return;
    }
    leaveExitDoneRef.current = false;
    const timerId = window.setTimeout(() => {
      if (leaveExitDoneRef.current) return;
      leaveExitDoneRef.current = true;
      onLeavingRemoveComplete();
    }, 450);
    return () => window.clearTimeout(timerId);
  }, [isLeaving, onLeavingRemoveComplete]);

  const pdfLink = recording.whiteboard_pdf_url?.trim();
  const hasPdf = !!pdfLink && /^https?:\/\//i.test(pdfLink);
  const isWhiteboardOnly = recording.kind === 'whiteboard_only';
  const dateLabel = recording.started_at
    ? new Intl.DateTimeFormat('ru-RU', {
        day: 'numeric',
        month: 'long',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date(recording.started_at))
    : 'Запись без даты';

  return (
    <article
      className={cn(styles.recordingCard, isLeaving && styles.recordingCardLeaving)}
      onAnimationEnd={(e) => {
        if (e.target !== e.currentTarget) return;
        if (!isLeaving || !onLeavingRemoveComplete) return;
        if (leaveExitDoneRef.current) return;
        leaveExitDoneRef.current = true;
        onLeavingRemoveComplete();
      }}
    >
      <div className={styles.recordingCardHead}>
        <h3 className={styles.recordingCardTitle}>
          {isWhiteboardOnly ? 'Доска вебинара' : dateLabel}
        </h3>
      </div>

      {!isWhiteboardOnly &&
        (recording.kinescope_upload_status === 'ready' &&
        stableEmbedUrl ? (
          <div className={styles.recordingIframeWrap}>
            <div
              ref={kinescopeContainerRef}
              className={styles.recordingIframe}
            />
          </div>
        ) : recording.kinescope_upload_status === 'failed' ? (
          <div className={styles.recordingFailed}>
            Не удалось обработать запись
          </div>
        ) : (
          <div className={styles.recordingStatus}>
            <span>Запись скоро появится</span>
          </div>
        ))}

      {hasPdf && (
        <div className={styles.whiteboardPdfRow}>
          <a
            className={styles.whiteboardPdfLink}
            href={pdfLink}
            target="_blank"
            rel="noopener noreferrer"
            download
          >
            <FileDown size={18} />
            Скачать PDF доски
          </a>
        </div>
      )}

      {isTeacher && recording.recording_id && (
        <div className={styles.recordingActions}>
          {!isWhiteboardOnly && (
            <button
              type="button"
              className={styles.recordingActionButton}
              onClick={() =>
                onRequestDeleteRecording({
                  recordingId: recording.recording_id,
                  dateLabel,
                })
              }
              disabled={deleteRecordingPending || isLeaving}
            >
              <Trash2 size={16} />
              {deleteRecordingPending || isLeaving ? 'Удаление...' : 'Удалить запись'}
            </button>
          )}
          {hasPdf && (
            <button
              type="button"
              className={styles.recordingActionButton}
              onClick={() =>
                onRequestDeletePdf({
                  recordingId: recording.recording_id,
                  dateLabel,
                })
              }
              disabled={deletePdfPending}
            >
              <Trash2 size={16} />
              {deletePdfPending ? 'Удаление...' : 'Удалить PDF'}
            </button>
          )}
        </div>
      )}
    </article>
  );
};

const TITLE_CENTER_MIN_WIDTH = 130;
const TITLE_CENTER_MAX_WIDTH = 560;

/* ── Page ── */

export default function LessonViewPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const navigate = useNavigate();
  const { hasAny } = useRole();
  const isTeacher = hasAny('teacher', 'moderator');

  const lessonQuery = useLessonBySlug(courseSlug, lessonSlug);

  const lessonDetail = lessonQuery.data;

  const webinarId = useMemo(() => {
    const m = lessonDetail?.meta as Record<string, unknown> | undefined;
    return typeof m?.webinar_id === 'string' ? m.webinar_id : null;
  }, [lessonDetail?.meta]);

  const [liveWebinarStatus, setLiveWebinarStatus] = useState<WebinarStatus | null>(
    lessonDetail?.webinar_status ?? null,
  );
  const [liveScheduledAt, setLiveScheduledAt] = useState<string | null>(
    lessonDetail?.scheduled_at ?? null,
  );

  useEffect(() => {
    setLiveWebinarStatus(lessonDetail?.webinar_status ?? null);
  }, [lessonDetail?.webinar_status]);
  useEffect(() => {
    setLiveScheduledAt(lessonDetail?.scheduled_at ?? null);
  }, [lessonDetail?.scheduled_at]);
  useEffect(() => {
    if (!webinarId) return;
    return connectWebinarSSE({
      webinarId,
      onEvent: (event) => {
        if (event.type === 'webinar_started' || event.type === 'webinar_start') {
          setLiveWebinarStatus('live');
          return;
        }
        if (event.type === 'webinar_ended' || event.type === 'webinar_end') {
          setLiveWebinarStatus('ended');
          return;
        }
        if (
          event.type === 'webinar_scheduled' ||
          event.type === 'webinar_schedule_changed'
        ) {
          setLiveScheduledAt(event.scheduled_at ?? null);
          setLiveWebinarStatus((prev) =>
            prev === 'live' ? prev : event.scheduled_at ? 'pending' : null,
          );
        }
      },
    });
  }, [webinarId]);

  const courseTitle =
    lessonDetail?.course_title
    ?? courseSlug?.replace(/-/g, ' ')
    ?? 'Курс';
  const deleteRecordingPdf = useDeleteRecordingPdf(courseSlug ?? '', lessonSlug ?? '');
  const deleteRecording = useDeleteRecording(courseSlug ?? '', lessonSlug ?? '');
  const [recordingDeleteConfirm, setRecordingDeleteConfirm] =
    useState<RecordingDeleteConfirm>(null);
  const [leavingRecordingId, setLeavingRecordingId] = useState<string | null>(null);
  const leavingRecordingIdRef = useRef<string | null>(null);
  const titleMeasureRef = useRef<HTMLSpanElement>(null);
  const [titleCenterWidth, setTitleCenterWidth] = useState(TITLE_CENTER_MIN_WIDTH);

  const completeRecordingLeaveAnimation = useCallback(() => {
    const id = leavingRecordingIdRef.current;
    if (!id) return;
    leavingRecordingIdRef.current = null;
    deleteRecording.mutate(id);
    setLeavingRecordingId(null);
  }, [deleteRecording]);

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

  useLayoutEffect(() => {
    const node = titleMeasureRef.current;
    if (!node) return;
    const measured = Math.ceil(node.getBoundingClientRect().width) + 44;
    setTitleCenterWidth(
      Math.min(
        TITLE_CENTER_MAX_WIDTH,
        Math.max(TITLE_CENTER_MIN_WIDTH, measured),
      ),
    );
  }, [lessonDetail?.title]);

  const loading = lessonQuery.isLoading;
  if (loading) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </PageFrame>
    );
  }

  if (lessonQuery.isError || !lessonDetail) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>
              Не удалось загрузить урок. Проверьте доступ и попробуйте снова.
            </p>
            <div className={styles.errorActions}>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate(-1)}
              >
                Назад
              </Button>
              <Button type="button" onClick={() => void lessonQuery.refetch()}>
                Попробовать снова
              </Button>
            </div>
          </div>
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <div className={styles.body}>
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
              <BreadcrumbLink asChild>
                <Link to={`/app/courses/${courseSlug}`}>{courseTitle}</Link>
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
              <svg
                className={styles.lessonHeaderCapLeft}
                width="36"
                height="50"
                viewBox="0 0 36 50"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden
              >
                <path
                  d="M0.526002 49.5C0.0639109 49.5 5.86287 35.1201 10.4607 7.34502C11.1094 3.42623 14.4713 0.5 18.4434 0.5H35.526C35.2499 0.5 35.026 0.73128 35.026 1.00742V49.0062C35.026 49.2823 35.2499 49.5 35.526 49.5H0.526002Z"
                  fill="#fff"
                  stroke="#fff"
                />
              </svg>
              <div
                className={styles.lessonHeaderCenter}
                style={{ width: `${titleCenterWidth}px` }}
              >
                <svg
                  className={styles.lessonHeaderCenterSvg}
                  width="82"
                  height="50"
                  viewBox="0 0 82 50"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  preserveAspectRatio="none"
                  aria-hidden
                >
                  <rect width="82" height="50" fill="#fff" />
                </svg>
                <h1 className={styles.lessonTitleTrapezoid}>
                  {lessonDetail.title}
                </h1>
                <span ref={titleMeasureRef} className={styles.titleMeasure}>
                  {lessonDetail.title || '\u00a0'}
                </span>
              </div>
              <svg
                className={styles.lessonHeaderCapRight}
                width="36"
                height="50"
                viewBox="0 0 36 50"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden
              >
                <path
                  d="M35.0052 49.5C35.4673 49.5 29.6684 35.1201 25.0705 7.34502C24.4218 3.42623 21.0599 0.5 17.0878 0.5H0.00523758C0.28138 0.5 0.505238 0.73128 0.505238 1.00742V49.0062C0.505238 49.2823 0.28138 49.5 0.00523758 49.5H35.0052Z"
                  fill="#fff"
                  stroke="#fff"
                />
              </svg>
            </div>
          </div>

          <main className={styles.main}>
            {lessonLayout && <LessonContent layout={lessonLayout} />}
            {lessonDetail.recordings.length > 0 && (
              <section className={styles.recordingSection}>
                <h2 className={styles.recordingTitle}>Записи вебинара</h2>
                <div className={styles.recordingList}>
                  {lessonDetail.recordings.map((recording) => (
                    <LessonRecordingCard
                      key={`${recording.recording_id}-${recording.started_at ?? 'recording'}`}
                      recording={recording}
                      isTeacher={isTeacher}
                      onRequestDeletePdf={({ recordingId, dateLabel }) => {
                        setRecordingDeleteConfirm({
                          kind: 'pdf',
                          recordingId,
                          dateLabel,
                        });
                      }}
                      onRequestDeleteRecording={({ recordingId, dateLabel }) => {
                        setRecordingDeleteConfirm({
                          kind: 'recording',
                          recordingId,
                          dateLabel,
                        });
                      }}
                      deletePdfPending={
                        deleteRecordingPdf.isPending &&
                        deleteRecordingPdf.variables === recording.recording_id
                      }
                      deleteRecordingPending={
                        deleteRecording.isPending &&
                        deleteRecording.variables === recording.recording_id
                      }
                      isLeaving={leavingRecordingId === recording.recording_id}
                      onLeavingRemoveComplete={
                        leavingRecordingId === recording.recording_id
                          ? completeRecordingLeaveAnimation
                          : undefined
                      }
                    />
                  ))}
                </div>
              </section>
            )}
          </main>
        </div>

        <aside className={styles.sidebar}>
          {(liveWebinarStatus === null ||
            liveWebinarStatus === 'pending') &&
            liveScheduledAt && (
              <TimerWidget targetIso={liveScheduledAt} />
            )}
          <WebinarWidget
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
            isTeacher={isTeacher}
            webinarStatus={liveWebinarStatus}
          />
          {isTeacher && (
            <LessonEditWidget
              courseSlug={courseSlug ?? ''}
              lessonSlug={lessonSlug ?? ''}
            />
          )}
          {isTeacher && (
            <WebinarScheduleWidget
              courseSlug={courseSlug ?? ''}
              lessonSlug={lessonSlug ?? ''}
              scheduledAt={liveScheduledAt}
            />
          )}
          <HomeworkWidget
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
            homeworks={lessonDetail.homeworks}
            isTeacher={isTeacher}
          />
          <ProgressWidget meta={lessonDetail.meta} />
          <AiChatPanel courseSlug={courseSlug ?? ''} />
        </aside>
      </div>
      </div>

      <AlertDialog
        open={recordingDeleteConfirm !== null}
        onOpenChange={(open) => {
          if (!open) setRecordingDeleteConfirm(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {recordingDeleteConfirm?.kind === 'pdf'
                ? 'Удалить PDF доски?'
                : 'Удалить запись?'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {recordingDeleteConfirm?.kind === 'pdf'
                ? `PDF для записи «${recordingDeleteConfirm.dateLabel}» будет удалён без возможности восстановления.`
                : `Запись «${recordingDeleteConfirm?.dateLabel ?? ''}» будет удалена без возможности восстановления.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRecordingDeleteConfirm(null)}>
              Отмена
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={
                recordingDeleteConfirm?.kind === 'pdf'
                  ? deleteRecordingPdf.isPending
                  : deleteRecording.isPending
              }
              onClick={() => {
                if (!recordingDeleteConfirm) return;
                if (recordingDeleteConfirm.kind === 'pdf') {
                  deleteRecordingPdf.mutate(recordingDeleteConfirm.recordingId);
                } else {
                  leavingRecordingIdRef.current = recordingDeleteConfirm.recordingId;
                  setLeavingRecordingId(recordingDeleteConfirm.recordingId);
                }
                setRecordingDeleteConfirm(null);
              }}
            >
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageFrame>
  );
}
