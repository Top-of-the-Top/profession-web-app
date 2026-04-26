import { Mic, MicOff, Video, VideoOff, Circle, LogOut, PhoneOff } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import styles from './WebinarControls.module.css';

interface WebinarControlsProps {
  micOn: boolean;
  cameraOn: boolean;
  isTeacher: boolean;
  isRecording: boolean;
  recordingPending: boolean;
  stopRecordingPending: boolean;
  stopWebinarPending: boolean;
  onToggleMic: () => void;
  onToggleCamera: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onLeave: () => void;
  onStopWebinar: () => void;
}

export function WebinarControls({
  micOn,
  cameraOn,
  isTeacher,
  isRecording,
  recordingPending,
  stopRecordingPending,
  stopWebinarPending,
  onToggleMic,
  onToggleCamera,
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

      {isTeacher && !isRecording && (
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

      {isTeacher && isRecording && (
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

      <div className={styles.spacer} />

      {isTeacher ? (
        <button
          type="button"
          className={cn(styles.btn, styles.btnDanger)}
          onClick={onStopWebinar}
          disabled={stopWebinarPending}
        >
          <PhoneOff size={18} />
          {stopWebinarPending ? 'Завершение...' : 'Завершить вебинар'}
        </button>
      ) : (
        <button
          type="button"
          className={cn(styles.btn, styles.btnDanger)}
          onClick={onLeave}
        >
          <LogOut size={18} />
          Покинуть
        </button>
      )}
    </div>
  );
}
