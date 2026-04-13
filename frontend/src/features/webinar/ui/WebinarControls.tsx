import { Mic, MicOff, Video, VideoOff, Circle, LogOut, PhoneOff } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import styles from './WebinarControls.module.css';

interface WebinarControlsProps {
  micOn: boolean;
  cameraOn: boolean;
  isTeacher: boolean;
  isRecording: boolean;
  recordingPending: boolean;
  stopPending: boolean;
  onToggleMic: () => void;
  onToggleCamera: () => void;
  onStartRecording: () => void;
  onLeave: () => void;
  onStop: () => void;
}

export function WebinarControls({
  micOn,
  cameraOn,
  isTeacher,
  isRecording,
  recordingPending,
  stopPending,
  onToggleMic,
  onToggleCamera,
  onStartRecording,
  onLeave,
  onStop,
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
        <button type="button" className={styles.btn} disabled>
          <span className={styles.recordingDot} />
          Запись идёт
        </button>
      )}

      <div className={styles.spacer} />

      {isTeacher ? (
        <button
          type="button"
          className={cn(styles.btn, styles.btnDanger)}
          onClick={onStop}
          disabled={stopPending}
        >
          <PhoneOff size={18} />
          {stopPending ? 'Завершение...' : 'Завершить вебинар'}
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
