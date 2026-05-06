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
  return (
    <div className={styles.bar}>
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
