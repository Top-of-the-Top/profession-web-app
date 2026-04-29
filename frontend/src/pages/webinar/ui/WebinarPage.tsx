import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, PageFrame, Spinner } from '@shared/ui';
import { useWebinarJoin } from '@shared/api/queries/webinar';
import { useLessonBySlug } from '@shared/api/queries/courses';
import {
  useStopRecording,
  useUploadRecordingPdf,
  useStartRecording,
  useStopWebinar,
} from '@shared/api/mutations/webinar';
import {
  VideoGrid,
  WhiteboardPanel,
  WebinarControls,
  useMediaControls,
  type WhiteboardPanelHandle,
} from '../../../features/webinar';
import { notifyError, notifyWarning } from '@shared/lib/sileo/notify';
import styles from './WebinarPage.module.css';

export default function WebinarPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const navigate = useNavigate();

  const joinQuery = useWebinarJoin(courseSlug, lessonSlug);
  const { data: session, isLoading, isError } = joinQuery;
  const lessonQuery = useLessonBySlug(courseSlug, lessonSlug);

  const { micOn, cameraOn, toggleMic, toggleCamera } = useMediaControls();

  const [activeRecordingId, setActiveRecordingId] = useState<string | null>(null);
  const [isFinishing, setIsFinishing] = useState(false);

  const whiteboardRef = useRef<WhiteboardPanelHandle>(null);

  const startRecording = useStartRecording(courseSlug ?? '', lessonSlug ?? '');
  const stopRecording = useStopRecording(courseSlug ?? '', lessonSlug ?? '');
  const uploadRecordingPdf = useUploadRecordingPdf(courseSlug ?? '', lessonSlug ?? '');
  const stopWebinar = useStopWebinar(courseSlug ?? '', lessonSlug ?? '');

  const isTeacher = session?.role === 'teacher';
  const isRecording = !!activeRecordingId;

  const captureWhiteboardScreenshots = useCallback(async () => {
    if (!whiteboardRef.current) {
      notifyError({
        title: 'доска не готова',
        description: 'Подождите, пока доска загрузится, и попробуйте снова.',
      });
      return null;
    }

    const screenshots = await whiteboardRef.current.captureSceneScreenshots();
    if (screenshots.length === 0) {
      notifyWarning({
        title: 'доска не сохранена',
        description: 'Не удалось снять скриншоты для PDF.',
      });
      return null;
    }

    return screenshots;
  }, []);

  const stopRecordingWithPdfUpload = useCallback(async () => {
    const stopResponse = await stopRecording.mutateAsync();
    setActiveRecordingId(null);

    const screenshots = await captureWhiteboardScreenshots();
    if (!screenshots || screenshots.length === 0) {
      return;
    }

    await uploadRecordingPdf.mutateAsync({
      recordingId: stopResponse.recording_id,
      screenshots,
    });
  }, [captureWhiteboardScreenshots, stopRecording, uploadRecordingPdf]);

  const handleStartRecording = useCallback(() => {
    startRecording.mutate(undefined, {
      onSuccess: (response) => setActiveRecordingId(response.recording_id),
    });
  }, [startRecording]);

  const handleStopRecording = useCallback(() => {
    void stopRecordingWithPdfUpload();
  }, [stopRecordingWithPdfUpload]);

  const handleLeave = useCallback(() => {
    navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
  }, [navigate, courseSlug, lessonSlug]);

  const handleStop = useCallback(async () => {
    setIsFinishing(true);
    try {
      if (activeRecordingId) {
        await stopRecordingWithPdfUpload();
      }
      await stopWebinar.mutateAsync();
      navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
    } catch {
      notifyError({
        title: 'не удалось завершить вебинар',
        description: 'Повторите попытку.',
      });
    } finally {
      setIsFinishing(false);
    }
  }, [
    activeRecordingId,
    stopRecordingWithPdfUpload,
    stopWebinar,
    navigate,
    courseSlug,
    lessonSlug,
  ]);

  useEffect(() => {
    if (activeRecordingId != null) return;
    const recording = lessonQuery.data?.recordings.find(
      (item) => item.status === 'recording' && item.recording_id,
    );
    if (recording?.recording_id) {
      setActiveRecordingId(recording.recording_id);
    }
  }, [activeRecordingId, lessonQuery.data?.recordings]);

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
        stopRecordingPending={
          stopRecording.isPending || uploadRecordingPdf.isPending
        }
        stopWebinarPending={isFinishing || stopWebinar.isPending}
        onToggleMic={toggleMic}
        onToggleCamera={toggleCamera}
        onStartRecording={handleStartRecording}
        onStopRecording={handleStopRecording}
        onLeave={handleLeave}
        onStopWebinar={() => void handleStop()}
      />
    </PageFrame>
  );
}
