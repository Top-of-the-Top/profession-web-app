import { useEffect, useMemo, useState } from 'react';
import { Mic, MicOff, Video, VideoOff, Circle, LogOut, PhoneOff, MessageSquare } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import styles from './WebinarControls.module.css';

interface WebinarControlsProps {
  micOn: boolean;
  cameraOn: boolean;
  canManageWebinar: boolean;
  teacherRecordingLive: boolean;
  studentRecordingVisible: boolean;
  recordingPending: boolean;
  stopRecordingPending: boolean;
  stopWebinarPending: boolean;
  webinarStartedAt: string | null;
  isChatOpen: boolean;
  onToggleMic: () => void;
  onToggleCamera: () => void;
  onToggleChat: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onLeave: () => void;
  onStopWebinar: () => void;
}

export function WebinarControls({
  micOn,
  cameraOn,
  canManageWebinar,
  teacherRecordingLive,
  studentRecordingVisible,
  recordingPending,
  stopRecordingPending,
  stopWebinarPending,
  webinarStartedAt,
  isChatOpen,
  onToggleMic,
  onToggleCamera,
  onToggleChat,
  onStartRecording,
  onStopRecording,
  onLeave,
  onStopWebinar,
}: WebinarControlsProps) {
  const webinarStartedAtMs = useMemo(() => {
    if (!webinarStartedAt) return null;
    const parsed = new Date(webinarStartedAt).getTime();
    return Number.isFinite(parsed) ? parsed : null;
  }, [webinarStartedAt]);

  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!webinarStartedAtMs) return;
    setNowMs(Date.now());
    const timerId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timerId);
  }, [webinarStartedAtMs]);

  const webinarDurationLabel = useMemo(() => {
    if (!webinarStartedAtMs) return null;
    const elapsedSeconds = Math.max(0, Math.floor((nowMs - webinarStartedAtMs) / 1000));
    const hours = Math.floor(elapsedSeconds / 3600);
    const minutes = Math.floor((elapsedSeconds % 3600) / 60);
    const seconds = elapsedSeconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }, [nowMs, webinarStartedAtMs]);

  return (
    <div className={styles.bar}>
      {webinarDurationLabel ? (
        <span className={styles.webinarDurationBadge}>В эфире {webinarDurationLabel}</span>
      ) : null}

      <button
        type="button"
        className={cn(styles.btn, micOn && styles.btnActive)}
        onClick={onToggleMic}
      >
        {micOn ? <Mic size={18} /> : <MicOff size={18} />}
        {micOn ? 'Микрофон' : 'Микрофон выкл'}
      </button>

      <button
        type="button"
        className={cn(styles.btn, cameraOn && styles.btnActive)}
        onClick={onToggleCamera}
      >
        {cameraOn ? <Video size={18} /> : <VideoOff size={18} />}
        {cameraOn ? 'Камера' : 'Камера выкл'}
      </button>

      <button
        type="button"
        className={cn(styles.btn, isChatOpen && styles.btnActive)}
        onClick={onToggleChat}
      >
        <MessageSquare size={18} />
        Чат
      </button>

      {canManageWebinar && !teacherRecordingLive && (
        <button
          type="button"
          className={styles.btn}
          onClick={onStartRecording}
          disabled={recordingPending}
        >
          <Circle size={16} />
          {recordingPending ? 'Запуск...' : 'Начать запись'}
        </button>
      )}

      {canManageWebinar && teacherRecordingLive && (
        <>
          <span className={styles.recordingBadge}>
            <span className={styles.recordingDot} />
            Запись идёт
          </span>
          <button
            type="button"
            className={styles.btn}
            onClick={onStopRecording}
            disabled={stopRecordingPending}
          >
            {stopRecordingPending ? 'Остановка...' : 'Остановить запись'}
          </button>
        </>
      )}

      {!canManageWebinar && studentRecordingVisible ? (
        <span className={styles.recordingBadge}>
          <span className={styles.recordingDot} />
          Запись идёт
        </span>
      ) : null}

      <div className={styles.spacer} />

      <button
        type="button"
        className={cn(styles.btn, styles.btnDanger)}
        onClick={onLeave}
      >
        <LogOut size={18} />
        Покинуть
      </button>
      {canManageWebinar && (
        <button
          type="button"
          className={cn(styles.btn, styles.btnDanger)}
          onClick={onStopWebinar}
          disabled={stopWebinarPending}
        >
          <PhoneOff size={18} />
          {stopWebinarPending ? 'Завершение...' : 'Завершить вебинар'}
        </button>
      )}
    </div>
  );
}
