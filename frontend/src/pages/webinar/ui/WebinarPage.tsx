import { useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, PageFrame, Spinner } from '@shared/ui';
import { useWebinarJoin } from '@shared/api/queries/webinar';
import { useStartRecording, useStopWebinar } from '@shared/api/mutations/webinar';
import {
  VideoGrid,
  WhiteboardPanel,
  WebinarControls,
  useMediaControls,
} from '../../../features/webinar';
import styles from './WebinarPage.module.css';

export default function WebinarPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const navigate = useNavigate();

  const joinQuery = useWebinarJoin(courseSlug, lessonSlug);
  const { data: session, isLoading, isError } = joinQuery;

  const { micOn, cameraOn, toggleMic, toggleCamera } = useMediaControls();

  const [isRecording, setIsRecording] = useState(false);

  const startRecording = useStartRecording(courseSlug ?? '', lessonSlug ?? '');
  const stopWebinar = useStopWebinar(courseSlug ?? '', lessonSlug ?? '');

  const isTeacher = session?.role === 'teacher';

  const handleStartRecording = useCallback(() => {
    startRecording.mutate(undefined, {
      onSuccess: () => setIsRecording(true),
    });
  }, [startRecording]);

  const handleLeave = useCallback(() => {
    navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
  }, [navigate, courseSlug, lessonSlug]);

  const handleStop = useCallback(() => {
    stopWebinar.mutate(undefined, {
      onSuccess: () => {
        navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
      },
    });
  }, [stopWebinar, navigate, courseSlug, lessonSlug]);

  if (isLoading) {
    return (
      <PageFrame className={styles.stateCenter}>
        <Spinner />
      </PageFrame>
    );
  }

  if (isError || !session) {
    return (
      <PageFrame className={styles.stateCenter}>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>
            Не удалось подключиться к вебинару. Проверьте, что вебинар запущен, и у вас есть доступ.
          </p>
          <div className={styles.errorActions}>
            <Button variant="outline" onClick={() => navigate(-1)}>
              Назад
            </Button>
            <Button onClick={() => void joinQuery.refetch()}>
              Попробовать снова
            </Button>
          </div>
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame className={styles.shell}>
      <div className={styles.body}>
        <div className={styles.whiteboardArea}>
          <WhiteboardPanel
            appIdentifier={session.whiteboard_app_id}
            roomUUID={session.whiteboard_room_uuid}
            roomToken={session.whiteboard_room_token}
            region={session.whiteboard_region}
            uid={String(session.uid)}
            isWritable={true}
          />
        </div>

        <div className={styles.videoSidebar}>
          <VideoGrid
            appId={session.agora_app_id}
            token={session.rtc_token}
            channel={session.channel_name}
            uid={session.uid}
            micOn={micOn}
            cameraOn={cameraOn}
          />
        </div>
      </div>

      <WebinarControls
        micOn={micOn}
        cameraOn={cameraOn}
        isTeacher={isTeacher}
        isRecording={isRecording}
        recordingPending={startRecording.isPending}
        stopPending={stopWebinar.isPending}
        onToggleMic={toggleMic}
        onToggleCamera={toggleCamera}
        onStartRecording={handleStartRecording}
        onLeave={handleLeave}
        onStop={handleStop}
      />
    </PageFrame>
  );
}
