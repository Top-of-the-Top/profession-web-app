import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { Button, Spinner } from '@shared/ui';
import { useRecorderJoin } from '@shared/api/queries/webinar';
import type { WebinarJoinResponse } from '@shared/api/webinarApi';
import { cn } from '@shared/lib/utils';
import { notifyError, notifySuccess } from '@shared/lib/sileo/notify';
import {
  VideoGrid,
  WhiteboardPanel,
  buildRtcUidLabelMap,
} from '../../../features/webinar';
import styles from './WebinarRecordPage.module.css';

function isRecorderSandboxMode(searchParams: URLSearchParams): boolean {
  return searchParams.get('sandbox') === '1';
}

function isRecorderDebugMode(searchParams: URLSearchParams): boolean {
  return import.meta.env.DEV && searchParams.get('debug') === '1';
}

function showRecorderAuxUi(searchParams: URLSearchParams): boolean {
  return isRecorderSandboxMode(searchParams) || isRecorderDebugMode(searchParams);
}

function redactJoinSession(s: WebinarJoinResponse) {
  return {
    rtc_token: `«${s.rtc_token.length} символов»`,
    whiteboard_room_token: `«${s.whiteboard_room_token.length} символов»`,
    agora_app_id: s.agora_app_id,
    channel_name: s.channel_name,
    uid: s.uid,
    user_name: s.user_name,
    whiteboard_app_id: s.whiteboard_app_id,
    whiteboard_room_uuid: s.whiteboard_room_uuid,
    whiteboard_region: s.whiteboard_region,
    role: s.role,
    webinar_id: s.webinar_id,
  };
}

function pickRecorderMimeType(): string {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
  ];
  for (const t of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) {
      return t;
    }
  }
  return 'video/webm';
}

function RecorderDebugPanel({
  session,
  courseSlug,
  lessonSlug,
  variant,
}: {
  session: WebinarJoinResponse | null;
  courseSlug: string;
  lessonSlug: string;
  variant: 'sandbox' | 'debug';
}) {
  const [expanded, setExpanded] = useState(true);
  const [localRecording, setLocalRecording] = useState(false);
  const [localSeconds, setLocalSeconds] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const displayStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      mediaRecorderRef.current?.stop();
      displayStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const copyRedacted = useCallback(async () => {
    if (!session) {
      notifyError({
        title: 'Нечего копировать',
        description: 'Сессия ещё не загружена.',
      });
      return;
    }
    const text = JSON.stringify(redactJoinSession(session), null, 2);
    try {
      await navigator.clipboard.writeText(text);
      notifySuccess({
        title: 'Скопировано',
        description: 'Данные сессии без токенов в буфере обмена.',
      });
    } catch {
      notifyError({
        title: 'Не удалось скопировать',
        description: 'Проверьте разрешения браузера.',
      });
    }
  }, [session]);

  const stopLocalRecording = useCallback(() => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'recording') {
      mr.requestData?.();
      mr.stop();
    } else {
      displayStreamRef.current?.getTracks().forEach((t) => t.stop());
      displayStreamRef.current = null;
      mediaRecorderRef.current = null;
    }
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    setLocalRecording(false);
    setLocalSeconds(0);
  }, []);

  const startLocalRecording = useCallback(async () => {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      notifyError({
        title: 'Запись недоступна',
        description: 'Браузер не поддерживает захват экрана.',
      });
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true,
      });
      displayStreamRef.current = stream;
      chunksRef.current = [];
      const mimeType = pickRecorderMimeType();
      const mr = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        mediaRecorderRef.current = null;
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || mimeType });
        stream.getTracks().forEach((t) => t.stop());
        displayStreamRef.current = null;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `recorder-${variant}-${courseSlug}-${lessonSlug}-${Date.now()}.webm`;
        a.click();
        URL.revokeObjectURL(url);
        notifySuccess({
          title: 'Файл сохранён',
          description: 'Локальная запись экрана скачана как .webm',
        });
      };
      stream.getVideoTracks()[0]?.addEventListener('ended', () => {
        stopLocalRecording();
      });
      mr.start(250);
      setLocalRecording(true);
      setLocalSeconds(0);
      tickRef.current = setInterval(() => {
        setLocalSeconds((s) => s + 1);
      }, 1000);
    } catch {
      notifyError({
        title: 'Захват отменён',
        description: 'Разрешите доступ к экрану или попробуйте снова.',
      });
    }
  }, [courseSlug, lessonSlug, stopLocalRecording, variant]);

  const mm = Math.floor(localSeconds / 60)
    .toString()
    .padStart(2, '0');
  const ss = (localSeconds % 60).toString().padStart(2, '0');

  return (
    <div className={styles.debugBar} data-expanded={expanded ? 'true' : 'false'}>
      <div className={styles.debugBarTop}>
        <div className={styles.debugBarTitleRow}>
          <span className={styles.debugBadge}>
            {variant === 'debug' ? 'Recorder · debug' : 'Recorder · sandbox'}
          </span>
          <span className={styles.debugHint}>
            {variant === 'debug' ? (
              <>
                только dev, <code className={styles.debugCode}>?debug=1</code>
              </>
            ) : (
              <>
                без токена, <code className={styles.debugCode}>?sandbox=1</code>
              </>
            )}
          </span>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className={styles.debugToggle}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? 'Свернуть' : 'Развернуть'}
        </Button>
      </div>

      {expanded ? (
        <div className={styles.debugBody}>
          <div className={styles.debugCol}>
            <p className={styles.debugSectionLabel}>Локальная запись (как у рекордера)</p>
            <p className={styles.debugMuted}>
              Захватывает выбранное окно или вкладку — проверка композиции без входа в эфир по
              токену.
            </p>
            <div className={styles.debugActions}>
              {!localRecording ? (
                <Button type="button" size="sm" onClick={() => void startLocalRecording()}>
                  Начать запись экрана
                </Button>
              ) : (
                <Button type="button" size="sm" variant="destructive" onClick={stopLocalRecording}>
                  Стоп · {mm}:{ss}
                </Button>
              )}
            </div>
          </div>

          <div className={styles.debugCol}>
            <p className={styles.debugSectionLabel}>Сессия Agora / доски</p>
            {session ? (
              <>
                <dl className={styles.debugDl}>
                  <dt>Канал</dt>
                  <dd>{session.channel_name}</dd>
                  <dt>UID</dt>
                  <dd>{session.uid}</dd>
                  <dt>Роль</dt>
                  <dd>{session.role}</dd>
                  <dt>App ID</dt>
                  <dd className={styles.debugMono}>{session.agora_app_id}</dd>
                </dl>
                <Button type="button" size="sm" variant="secondary" onClick={() => void copyRedacted()}>
                  Копировать JSON (без секретов)
                </Button>
              </>
            ) : (
              <p className={styles.debugMuted}>
                Нет сессии Agora / доски. Для реального эфира откройте ту же страницу с{' '}
                <code className={styles.debugCode}>?token=…</code> (без{' '}
                <code className={styles.debugCode}>sandbox=1</code>).
              </p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function WebinarRecordPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const recorderDevDebug = isRecorderDebugMode(searchParams);
  const showAuxPanel = showRecorderAuxUi(searchParams);
  const panelVariant = recorderDevDebug ? 'debug' : 'sandbox';

  const joinQuery = useRecorderJoin(courseSlug, lessonSlug, token);
  const { data: session, isLoading, isError } = joinQuery;

  const rtcUidToLabel = useMemo(() => {
    if (!session) return undefined;
    return buildRtcUidLabelMap({
      uid: session.uid,
      userName: session.user_name,
    });
  }, [session]);

  if (!token && !showAuxPanel) {
    const sandboxTo = {
      pathname: location.pathname,
      search: '?sandbox=1',
    } as const;

    return (
      <div className={styles.stateCenter}>
        <div className={styles.errorBox}>
          <p className={styles.errorTitle}>Нет токена записи</p>
          <p className={styles.errorText}>
            Для выхода в эфир нужна ссылка с параметром <code className={styles.inlineCode}>token</code>,
            которую выдаёт система. Если нужно только проверить запись экрана на этой странице — откройте
            режим песочницы.
          </p>
          <div className={styles.errorActions}>
            <Button asChild>
              <Link to={sandboxTo}>Режим песочницы (без токена)</Link>
            </Button>
          </div>
          <p className={styles.errorFootnote}>
            Или вручную добавьте в адресную строку{' '}
            <code className={styles.inlineCode}>?sandbox=1</code>
          </p>
        </div>
      </div>
    );
  }

  if (!token && showAuxPanel) {
    return (
      <div className={cn(styles.shell, styles.shellDebugPad)}>
        <RecorderDebugPanel
          variant={panelVariant}
          session={null}
          courseSlug={courseSlug ?? ''}
          lessonSlug={lessonSlug ?? ''}
        />
        <div className={styles.body}>
          <div className={styles.debugPlaceholder}>
            <p className={styles.debugPlaceholderTitle}>Песочница рекордера</p>
            <p className={styles.debugPlaceholderText}>
              Подключение к доске и Agora без токена недоступно. Снизу можно записать экран
              локально; для эфира используйте ссылку с выданным{' '}
              <code className={styles.inlineCode}>token</code>.
            </p>
          </div>
          <div className={styles.videoSidebar} />
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.stateCenter}>
        {showAuxPanel ? (
          <RecorderDebugPanel
            variant={panelVariant}
            session={null}
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
          />
        ) : null}
        <Spinner />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className={styles.stateCenter}>
        {showAuxPanel ? (
          <RecorderDebugPanel
            variant={panelVariant}
            session={null}
            courseSlug={courseSlug ?? ''}
            lessonSlug={lessonSlug ?? ''}
          />
        ) : null}
        <div className={styles.errorBox}>
          <p className={styles.errorTitle}>Не удалось открыть запись</p>
          <p className={styles.errorText}>
            Токен недействителен или вебинар уже завершён.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(styles.shell, showAuxPanel && styles.shellDebugPad)}>
      {showAuxPanel ? (
        <RecorderDebugPanel
          variant={panelVariant}
          session={session}
          courseSlug={courseSlug ?? ''}
          lessonSlug={lessonSlug ?? ''}
        />
      ) : null}
      <div className={styles.body}>
        <div className={styles.whiteboardArea}>
          <WhiteboardPanel
            appIdentifier={session.whiteboard_app_id}
            roomUUID={session.whiteboard_room_uuid}
            roomToken={session.whiteboard_room_token}
            region={session.whiteboard_region}
            uid={session.user_name?.trim() || String(session.uid)}
            userName={session.user_name}
            isWritable={false}
          />
        </div>

        <div className={styles.videoSidebar}>
          <VideoGrid
            appId={session.agora_app_id}
            token={session.rtc_token}
            channel={session.channel_name}
            uid={session.uid}
            rtcUidToLabel={rtcUidToLabel}
            subscribeOnly
          />
        </div>
      </div>
    </div>
  );
}
