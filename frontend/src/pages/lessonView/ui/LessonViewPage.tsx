import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
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
  Spinner,
} from '@shared/ui';
import type { LessonLayout, Block } from '../../../features/course-builder';
import {
  FONT_SIZE_STEPS,
  DEFAULT_FONT_SIZE_INDEX,
} from '../../../features/course-builder/lib/constants';
import { parseLessonLayoutFromContentString } from '../../../features/course-builder/model/types';
import type {
  HomeworkAttemptStatus,
  LessonRecording,
  LessonHomework,
  WebinarStatus,
} from '@shared/api/courseApi';
import { courseApi } from '@shared/api/courseApi';
import {
  courseKeys,
  useCourseHomeBySlug,
  useLessonBySlug,
} from '@shared/api/queries/courses';
import {
  useDeleteRecording,
  useDeleteRecordingPdf,
  useStartWebinar,
} from '@shared/api/mutations/webinar';
import { useToggleHomeworkType } from '@shared/api/mutations/courses';
import { useRole } from '@shared/lib/rbac';
import { cn } from '@shared/lib/utils';
import { AiChatPanel } from '../../../features/ai-chat';
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
  const attemptQueries = useQueries({
    queries: isTeacher
      ? []
      : visible.map((homework) => ({
          queryKey: courseKeys.homeworkAttempt(homework.homework_slug),
          queryFn: () => courseApi.getHomeworkAttempt(homework.homework_slug),
          staleTime: 30_000,
        })),
  });
  const attemptStatuses = useMemo(() => {
    const map = new Map<string, HomeworkAttemptStatus>();
    if (isTeacher) return map;
    for (let i = 0; i < visible.length; i += 1) {
      const slug = visible[i]?.homework_slug;
      const status = attemptQueries[i]?.data?.status;
      if (slug && status) {
        map.set(slug, status);
      }
    }
    return map;
  }, [attemptQueries, isTeacher, visible]);

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
          {!isTeacher && (
            <div className={styles.homeworkStatusRow}>
              <span
                className={
                  attemptStatuses.get(hw.homework_slug) === 'reviewed'
                    ? styles.hwBadgePublished
                    : attemptStatuses.get(hw.homework_slug) === 'submitted'
                      ? styles.hwBadgeDraft
                      : styles.hwBadgePending
                }
              >
                {attemptStatuses.get(hw.homework_slug) === 'reviewed'
                  ? 'проверено'
                  : attemptStatuses.get(hw.homework_slug) === 'submitted'
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
          <Link
            to={`/app/courses/${courseSlug}/${lessonSlug}/homework/${encodeURIComponent(hw.homework_slug)}`}
            className={styles.homeworkButton}
          >
            {attemptStatuses.get(hw.homework_slug) === 'reviewed'
              ? 'Посмотреть результат'
              : attemptStatuses.get(hw.homework_slug) === 'submitted'
                ? 'Посмотреть отправку'
                : hw.title || 'Сдать ДЗ'}
          </Link>
        </div>
      ))}
    </div>
  );
};

const ProgressWidget: React.FC = () => {
  const passedLessons = { done: 12, total: 24 };
  const submittedHomeworks = { done: 8, total: 11 };

  const passedPct = Math.round(
    (passedLessons.done / passedLessons.total) * 100
  );
  const submittedPct = Math.round(
    (submittedHomeworks.done / submittedHomeworks.total) * 100
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

  const webinarUrl = `/app/courses/${courseSlug}/${lessonSlug}/webinar`;

  const handleStartWebinar = () => {
    startWebinar.mutate(undefined, {
      onSuccess: () => navigate(webinarUrl),
    });
  };

  const handleJoinLive = () => {
    navigate(webinarUrl);
  };

  if (webinarStatus === 'live') {
    return (
      <div className={styles.linksRow}>
        <button
          type="button"
          className={styles.quickLinkButton}
          onClick={handleJoinLive}
        >
          <Video size={20} />
          <span>{isTeacher ? 'Вернуться в звонок' : 'Войти в вебинар'}</span>
        </button>
      </div>
    );
  }

  if (!isTeacher) {
    if (webinarStatus === 'pending') {
      return (
        <div className={styles.linksRow}>
          <button
            type="button"
            className={styles.quickLinkButton}
            onClick={handleJoinLive}
          >
            <Video size={20} />
            <span>Войти в вебинар</span>
          </button>
        </div>
      );
    }
    return null;
  }

  return (
    <div className={styles.linksRow}>
      <button
        type="button"
        className={styles.quickLinkButton}
        onClick={handleStartWebinar}
        disabled={startWebinar.isPending}
      >
        <Video size={20} />
        <span>{startWebinar.isPending ? 'Запуск...' : 'Начать вебинар'}</span>
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
        <h3 className={styles.recordingCardTitle}>{dateLabel}</h3>
      </div>

      {recording.kinescope_upload_status === 'ready' &&
      recording.kinescope_embed_url ? (
        <div className={styles.recordingIframeWrap}>
          <iframe
            src={recording.kinescope_embed_url}
            allow="autoplay; fullscreen; picture-in-picture; encrypted-media"
            allowFullScreen
            className={styles.recordingIframe}
            title="Запись урока"
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
      )}

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
              <FileDown size={16} />
              {deletePdfPending ? 'Удаление...' : 'Удалить PDF'}
            </button>
          )}
        </div>
      )}
    </article>
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
    homeQuery.data?.title ?? courseSlug?.replace(/-/g, ' ') ?? 'Курс';

  const lessonDetail = lessonQuery.data;
  const deleteRecordingPdf = useDeleteRecordingPdf(courseSlug ?? '', lessonSlug ?? '');
  const deleteRecording = useDeleteRecording(courseSlug ?? '', lessonSlug ?? '');
  const [recordingDeleteConfirm, setRecordingDeleteConfirm] =
    useState<RecordingDeleteConfirm>(null);
  const [leavingRecordingId, setLeavingRecordingId] = useState<string | null>(null);
  const leavingRecordingIdRef = useRef<string | null>(null);

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
              <h1 className={styles.lessonTitleTrapezoid}>
                {lessonDetail.title}
              </h1>
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
          {(lessonDetail.webinar_status === null ||
            lessonDetail.webinar_status === 'pending') &&
            lessonDetail.started_at && (
              <TimerWidget targetIso={lessonDetail.started_at} />
            )}
          <WebinarWidget
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
            isTeacher={isTeacher}
            webinarStatus={lessonDetail.webinar_status}
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
