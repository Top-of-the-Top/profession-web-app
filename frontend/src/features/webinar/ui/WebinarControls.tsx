import { useEffect, useRef, useState } from 'react';
import { Mic, MicOff, Video, VideoOff, LogOut, PhoneOff, MessageSquare } from 'lucide-react';

const StopIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
    <rect x="0" y="0" width="12" height="12" rx="3" />
  </svg>
);

const PlayIcon = () => (
  <svg width="13" height="13" viewBox="0 0 13 13" fill="currentColor">
    <polygon points="2,1 12,6.5 2,12" />
  </svg>
);
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
  isChatOpen,
  onToggleMic,
  onToggleCamera,
  onToggleChat,
  onStartRecording,
  onStopRecording,
  onLeave,
  onStopWebinar,
}: WebinarControlsProps) {
  const [leaveMenuOpen, setLeaveMenuOpen] = useState(false);
  const leaveMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!leaveMenuOpen) return;
    const handler = (e: MouseEvent) => {
      if (leaveMenuRef.current && !leaveMenuRef.current.contains(e.target as Node)) {
        setLeaveMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [leaveMenuOpen]);

  return (
    <div className={styles.bar}>
      <button
        type="button"
        className={cn(styles.btn, micOn && styles.btnActive)}
        onClick={onToggleMic}
      >
        {micOn ? <Mic size={18} /> : <MicOff size={18} />}
        {/* {micOn ? 'Микрофон' : 'Микрофон выкл'} */}
      </button>

      <button
        type="button"
        className={cn(styles.btn, cameraOn && styles.btnActive)}
        onClick={onToggleCamera}
      >
        {cameraOn ? <Video size={18} /> : <VideoOff size={18} />}
        {/* {cameraOn ? 'Камера' : 'Камера выкл'} */}
      </button>

      <button
        type="button"
        className={cn(styles.btn, isChatOpen && styles.btnActive)}
        onClick={onToggleChat}
      >
        <MessageSquare size={18} />
        Чат
      </button>

      {canManageWebinar && (
        <button
          type="button"
          className={cn(styles.btn, styles.btnRecord, teacherRecordingLive && styles.btnRecordLive)}
          onClick={teacherRecordingLive ? onStopRecording : onStartRecording}
          disabled={recordingPending || stopRecordingPending}
        >
          <span className={styles.recordingDotInline} />
          <span className={styles.recordIconPlay}><PlayIcon /></span>
          <span className={styles.recordIconStop}><StopIcon /></span>
          {stopRecordingPending ? (
            <span>Остановка...</span>
          ) : recordingPending ? (
            <span>Начинаем...</span>
          ) : (
            <>
              <span className={styles.recordLabelDefault}>Запись</span>
              <span className={styles.recordLabelHover}>
                {teacherRecordingLive ? 'Остановить' : 'Начать'}
              </span>
            </>
          )}
        </button>
      )}

      {!canManageWebinar && studentRecordingVisible && (
        <span className={styles.recordingBadge}>
          <span className={styles.recordingDot} />
          Запись идёт
        </span>
      )}

      <div className={styles.spacer} />

      <div className={styles.leaveMenuWrap} ref={leaveMenuRef}>
        {leaveMenuOpen && (
          <div className={styles.leaveMenu}>
            <button
              type="button"
              className={styles.leaveMenuItem}
              onClick={() => { setLeaveMenuOpen(false); onLeave(); }}
            >
              <LogOut size={15} />
              Выйти
            </button>
            {canManageWebinar && (
              <button
                type="button"
                className={cn(styles.leaveMenuItem, styles.leaveMenuItemDanger)}
                disabled={stopWebinarPending}
                onClick={() => { setLeaveMenuOpen(false); onStopWebinar(); }}
              >
                <PhoneOff size={15} />
                {stopWebinarPending ? 'Завершение...' : 'Завершить вебинар'}
              </button>
            )}
          </div>
        )}
        <button
          type="button"
          className={cn(styles.btn, styles.btnDanger)}
          onClick={() => setLeaveMenuOpen((v) => !v)}
        >
          <PhoneOff size={18} />
        </button>
      </div>
    </div>
  );
}
