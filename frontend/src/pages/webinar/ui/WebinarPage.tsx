import { useCallback, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, PageFrame, Spinner } from '@shared/ui';
import { useWebinarJoin } from '@shared/api/queries/webinar';
import {
  useStartRecording,
  useStopWebinar,
  useWhiteboardPdf,
} from '@shared/api/mutations/webinar';
import {
  VideoGrid,
  WhiteboardPanel,
  WebinarControls,
  useMediaControls,
  type WhiteboardPanelHandle,
} from '../../../features/webinar';
import { notifyError } from '@shared/lib/sileo/notify';
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
  const [isFinishing, setIsFinishing] = useState(false);

  const whiteboardRef = useRef<WhiteboardPanelHandle>(null);

  const startRecording = useStartRecording(courseSlug ?? '', lessonSlug ?? '');
  const whiteboardPdf = useWhiteboardPdf(courseSlug ?? '', lessonSlug ?? '');
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

  const handleStop = useCallback(async () => {
    if (!whiteboardRef.current) {
      notifyError({
        title: 'доска не готова',
        description: 'Подождите, пока доска загрузится, и попробуйте снова.',
      });
      return;
    }

    setIsFinishing(true);
    try {
      const screenshots = await whiteboardRef.current.captureSceneScreenshots();

      if (screenshots.length === 0) {
        notifyError({
          title: 'нет содержимого',
          description: 'Добавьте хотя бы одну сцену доски перед завершением.',
        });
        return;
      }

      await whiteboardPdf.mutateAsync(screenshots);
      await stopWebinar.mutateAsync();
      navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
    } catch {
      // Ошибки уже показаны тостами из mutation-хуков.
    } finally {
      setIsFinishing(false);
    }
  }, [whiteboardPdf, stopWebinar, navigate, courseSlug, lessonSlug]);

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
            ref={whiteboardRef}
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
        stopPending={
          isFinishing || whiteboardPdf.isPending || stopWebinar.isPending
        }
        onToggleMic={toggleMic}
        onToggleCamera={toggleCamera}
        onStartRecording={handleStartRecording}
        onLeave={handleLeave}
        onStop={() => void handleStop()}
      />
    </PageFrame>
  );
}
