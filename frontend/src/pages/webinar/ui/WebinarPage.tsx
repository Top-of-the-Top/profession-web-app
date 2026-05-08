import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { XIcon } from 'lucide-react';
import { Button, PageFrame, Spinner } from '@shared/ui';
import { useWebinarJoin } from '@shared/api/queries/webinar';
import { courseKeys, useLessonBySlug } from '@shared/api/queries/courses';
import {
  useStopRecording,
  useUploadRecordingPdf,
  useUploadFinalPdf,
  useStartRecording,
  useStopWebinar,
} from '@shared/api/mutations/webinar';
import {
  VideoGrid,
  WhiteboardPanel,
  WebinarControls,
  WebinarChat,
  connectWebinarSSE,
  useMediaControls,
  useWebinarChat,
  useWebinarHeartbeat,
  buildRtcUidLabelMap,
  type WhiteboardPanelHandle,
} from '../../../features/webinar';
import { notifyError, notifySuccess, notifyWarning } from '@shared/lib/sileo/notify';
import styles from './WebinarPage.module.css';

export default function WebinarPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const joinQuery = useWebinarJoin(courseSlug, lessonSlug);
  const { data: session, isLoading, isError } = joinQuery;
  const lessonQuery = useLessonBySlug(courseSlug, lessonSlug);

  const [rtcUidToLabel, setRtcUidToLabel] = useState<Record<number, string> | undefined>(undefined);
  useEffect(() => {
    if (!session) return;
    setRtcUidToLabel(
      buildRtcUidLabelMap({ uid: session.uid, userName: session.user_name, includeRecorderSlot: true }),
    );
  }, [session]);

  const handlePeerLabel = useCallback((rtcUid: number, label: string) => {
    setRtcUidToLabel((prev) => {
      if (prev?.[rtcUid] === label) return prev;
      return { ...prev, [rtcUid]: label };
    });
  }, []);

  const { micOn, cameraOn, toggleMic, toggleCamera } = useMediaControls();

  const { messages: chatMessages, sendMessage, broadcastPresence } = useWebinarChat({
    appId: session?.agora_app_id ?? '',
    rtmToken: session?.rtm_token ?? '',
    chatChannelName: session?.chat_channel_name ?? '',
    uid: session?.uid ?? 0,
    userName: session?.user_name ?? '',
    onPeerLabel: handlePeerLabel,
  });

  const [isChatOpen, setIsChatOpen] = useState(false);
  const handleToggleChat = useCallback(() => setIsChatOpen((v) => !v), []);

  const [activeRecordingId, setActiveRecordingId] = useState<string | null>(null);
  const [recorderBotInChannel, setRecorderBotInChannel] = useState(false);
  const [awaitingRecorderBot, setAwaitingRecorderBot] = useState(false);
  const [awaitingRecordingSessionEnd, setAwaitingRecordingSessionEnd] =
    useState(false);
  const [isFinishing, setIsFinishing] = useState(false);
  const [isExitWithoutRecordingDialogOpen, setIsExitWithoutRecordingDialogOpen] =
    useState(false);
  const hasWarnedAboutMissingWebinarIdRef = useRef(false);
  const didSyncRecordingFromLessonRef = useRef(false);
  const recorderBotInChannelRef = useRef(false);
  const recordingLiveToastShownForIdRef = useRef<string | null>(null);
  const prevRecordingBroadcastLiveRef = useRef(false);

  const whiteboardRef = useRef<WhiteboardPanelHandle>(null);

  const startRecording = useStartRecording(courseSlug ?? '', lessonSlug ?? '');
  const stopRecording = useStopRecording(courseSlug ?? '', lessonSlug ?? '');
  const uploadRecordingPdf = useUploadRecordingPdf(courseSlug ?? '', lessonSlug ?? '');
  const uploadFinalPdf = useUploadFinalPdf(courseSlug ?? '', lessonSlug ?? '');
  const stopWebinar = useStopWebinar(courseSlug ?? '', lessonSlug ?? '');

  const canManageWebinar =
    session?.role === 'teacher' || session?.role === 'moderator';
  const recordingBroadcastLive = !!activeRecordingId && recorderBotInChannel;
  const teacherRecordingLive = recordingBroadcastLive;
  const studentRecordingVisible = recordingBroadcastLive;
  const recordingSessionActive =
    !!activeRecordingId || recorderBotInChannel || awaitingRecorderBot;

  useEffect(() => {
    recorderBotInChannelRef.current = recorderBotInChannel;
  }, [recorderBotInChannel]);

  useEffect(() => {
    if (recorderBotInChannel && awaitingRecorderBot) {
      setAwaitingRecorderBot(false);
    }
  }, [recorderBotInChannel, awaitingRecorderBot]);

  const handleRecorderChannelPresence = useCallback((present: boolean) => {
    setRecorderBotInChannel(present);
  }, []);

  const captureWhiteboardScreenshots = useCallback(async () => {
    console.log('[whiteboard capture]', 'WebinarPage: captureWhiteboardScreenshots start');
    if (!whiteboardRef.current) {
      console.warn('[whiteboard capture]', 'WebinarPage: whiteboardRef is null');
      notifyError({
        title: 'доска не готова',
        description: 'Подождите, пока доска загрузится, и попробуйте снова.',
      });
      return null;
    }

    const screenshots = await whiteboardRef.current.captureSceneScreenshots();
    console.log('[whiteboard capture]', 'WebinarPage: captureSceneScreenshots result', {
      count: screenshots.length,
      bytes: screenshots.reduce((n, b) => n + b.size, 0),
    });
    if (screenshots.length === 0) {
      notifyWarning({
        title: 'доска не сохранена',
        description: 'Не удалось снять скриншоты для PDF.',
      });
      return null;
    }

    return screenshots;
  }, []);

  const stopRecordingWithOptionalPdfUpload = useCallback(async (screenshots?: Blob[] | null) => {
    let stopResponse: Awaited<ReturnType<typeof stopRecording.mutateAsync>>;
    try {
      stopResponse = await stopRecording.mutateAsync();
    } catch {
      return;
    }
    setAwaitingRecordingSessionEnd(true);

    const screenshotsToUpload =
      screenshots && screenshots.length > 0
        ? screenshots
        : await captureWhiteboardScreenshots();

    if (!screenshotsToUpload || screenshotsToUpload.length === 0) {
      notifyWarning({
        title: 'запись остановлена без PDF',
        description: 'Не удалось сохранить PDF доски для этой записи.',
      });
      return;
    }

    try {
      await uploadRecordingPdf.mutateAsync({
        recordingId: stopResponse.recording_id,
        screenshots: screenshotsToUpload,
      });
    } catch {
      notifyWarning({
        title: 'запись остановлена без PDF',
        description: 'Не удалось загрузить скриншоты доски. Видео продолжит обработку.',
      });
    }
  }, [captureWhiteboardScreenshots, stopRecording, uploadRecordingPdf]);

  const handleStartRecording = useCallback(() => {
    startRecording.mutate(undefined, {
      onSuccess: (response) => {
        setActiveRecordingId(response.recording_id);
        if (!recorderBotInChannelRef.current) {
          setAwaitingRecorderBot(true);
        }
      },
      onError: () => setAwaitingRecorderBot(false),
    });
  }, [startRecording]);

  const handleStopRecording = useCallback(() => {
    void (async () => {
      await stopRecordingWithOptionalPdfUpload();
    })();
  }, [stopRecordingWithOptionalPdfUpload]);

  const handleLeave = useCallback(() => {
    navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
  }, [navigate, courseSlug, lessonSlug]);

  const handleStop = useCallback(async () => {
    setIsFinishing(true);
    try {
      const screenshots = await captureWhiteboardScreenshots();
      if (recordingSessionActive) {
        await stopRecordingWithOptionalPdfUpload(screenshots);
      }
      if (!screenshots || screenshots.length === 0) {
        setIsExitWithoutRecordingDialogOpen(true);
        return;
      }
      await uploadFinalPdf.mutateAsync({ screenshots });
      await stopWebinar.mutateAsync();
      navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
    } catch {
      setIsExitWithoutRecordingDialogOpen(true);
    } finally {
      setIsFinishing(false);
    }
  }, [
    recordingSessionActive,
    stopRecordingWithOptionalPdfUpload,
    captureWhiteboardScreenshots,
    uploadFinalPdf,
    stopWebinar,
    navigate,
    courseSlug,
    lessonSlug,
  ]);

  const handleStopWithoutRecording = useCallback(async () => {
    setIsFinishing(true);
    try {
      await stopWebinar.mutateAsync();
      setIsExitWithoutRecordingDialogOpen(false);
      navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
    } catch {
      notifyError({
        title: 'не удалось завершить вебинар',
        description: 'Повторите попытку.',
      });
    } finally {
      setIsFinishing(false);
    }
  }, [courseSlug, lessonSlug, navigate, stopWebinar]);

  const closeExitDialog = useCallback(() => {
    if (isFinishing) return;
    setIsExitWithoutRecordingDialogOpen(false);
  }, [isFinishing]);

  const webinarIdFromMeta =
    lessonQuery.data?.meta &&
    typeof lessonQuery.data.meta === 'object' &&
    typeof lessonQuery.data.meta.webinar_id === 'string'
      ? lessonQuery.data.meta.webinar_id
      : null;
  const webinarId = session?.webinar_id ?? webinarIdFromMeta;
  const isStudent = session?.role === 'student';
  useWebinarHeartbeat(webinarId, !!session && isStudent);

  useEffect(() => {
    if (!session) return;
    if (webinarId) {
      hasWarnedAboutMissingWebinarIdRef.current = false;
      return;
    }
    if (hasWarnedAboutMissingWebinarIdRef.current) return;
    hasWarnedAboutMissingWebinarIdRef.current = true;
    notifyWarning({
      title: 'SSE не подключен',
      description:
        'Сервер не вернул webinar_id, поэтому авто-синхронизация событий временно недоступна.',
    });
  }, [session, webinarId]);

  useEffect(() => {
    if (!webinarId) return;

    const disconnect = connectWebinarSSE({
      webinarId,
      onEvent: (event) => {
        if (event.type === 'recording_started') {
          setActiveRecordingId((prev) =>
            prev === event.recording_id ? prev : event.recording_id,
          );
          return;
        }
        if (event.type === 'recording_stopped') {
          if (courseSlug && lessonSlug) {
            void queryClient.invalidateQueries({
              queryKey: courseKeys.lesson(courseSlug, lessonSlug),
            });
          }
          return;
        }
        if (event.type === 'webinar_ended') {
          navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
        }
      },
      onError: (message) => {
        notifyWarning({
          title: 'онлайн-обновления недоступны',
          description: message,
        });
      },
    });

    return disconnect;
  }, [courseSlug, lessonSlug, navigate, queryClient, webinarId]);

  useEffect(() => {
    if (!activeRecordingId) {
      recordingLiveToastShownForIdRef.current = null;
      return;
    }
    if (!recorderBotInChannel) return;
    if (recordingLiveToastShownForIdRef.current === activeRecordingId) return;
    recordingLiveToastShownForIdRef.current = activeRecordingId;
    notifySuccess({
      title: 'Запись началась',
    });
  }, [activeRecordingId, recorderBotInChannel]);

  useEffect(() => {
    const prev = prevRecordingBroadcastLiveRef.current;
    if (prev && !recordingBroadcastLive) {
      notifySuccess({
        title: 'Запись остановлена',
      });
      setActiveRecordingId(null);
      setAwaitingRecorderBot(false);
      setAwaitingRecordingSessionEnd(false);
      recordingLiveToastShownForIdRef.current = null;
      if (courseSlug && lessonSlug) {
        void queryClient.invalidateQueries({
          queryKey: courseKeys.lesson(courseSlug, lessonSlug),
        });
      }
    }
    prevRecordingBroadcastLiveRef.current = recordingBroadcastLive;
  }, [recordingBroadcastLive, courseSlug, lessonSlug, queryClient]);

  useEffect(() => {
    if (didSyncRecordingFromLessonRef.current) return;
    if (!lessonQuery.isSuccess || !lessonQuery.data) return;
    didSyncRecordingFromLessonRef.current = true;
    const recording = lessonQuery.data.recordings.find(
      (item) => item.status === 'recording' && item.recording_id,
    );
    if (recording?.recording_id) {
      setActiveRecordingId(recording.recording_id);
      if (!recorderBotInChannelRef.current) {
        setAwaitingRecorderBot(true);
      }
    }
  }, [lessonQuery.isSuccess, lessonQuery.data]);

  useEffect(() => {
    if (!isExitWithoutRecordingDialogOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        closeExitDialog();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [closeExitDialog, isExitWithoutRecordingDialogOpen]);

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
            uid={session.user_name?.trim() || String(session.uid)}
            userName={session.user_name}
            isWritable={true}
          />
        </div>

        <div className={styles.videoSidebar}>
          <VideoGrid
            appId={session.agora_app_id}
            token={session.rtc_token}
            channel={session.channel_name}
            uid={session.uid}
            rtcUidToLabel={rtcUidToLabel}
            onRecorderChannelPresence={handleRecorderChannelPresence}
            onRemoteUserJoined={broadcastPresence}
            micOn={micOn}
            cameraOn={cameraOn}
          >
            {isChatOpen && (
              <WebinarChat
                messages={chatMessages}
                uid={session.uid}
                sendMessage={sendMessage}
              />
            )}
          </VideoGrid>
        </div>
      </div>

      <WebinarControls
        micOn={micOn}
        cameraOn={cameraOn}
        isChatOpen={isChatOpen}
        canManageWebinar={canManageWebinar}
        teacherRecordingLive={teacherRecordingLive}
        studentRecordingVisible={studentRecordingVisible}
        recordingPending={startRecording.isPending || awaitingRecorderBot}
        stopRecordingPending={
          stopRecording.isPending ||
          uploadRecordingPdf.isPending ||
          awaitingRecordingSessionEnd
        }
        stopWebinarPending={
          isFinishing || stopWebinar.isPending || uploadFinalPdf.isPending
        }
        onToggleMic={toggleMic}
        onToggleCamera={toggleCamera}
        onToggleChat={handleToggleChat}
        onStartRecording={handleStartRecording}
        onStopRecording={handleStopRecording}
        onLeave={handleLeave}
        onStopWebinar={() => void handleStop()}
      />

      {isExitWithoutRecordingDialogOpen ? (
        <>
          <div
            className={styles.exitDialogOverlay}
            onClick={closeExitDialog}
            aria-hidden
          />
          <div
            className={styles.exitDialogContent}
            role="dialog"
            aria-modal="true"
            aria-labelledby="exit-dialog-title"
            aria-describedby="exit-dialog-description">
            {!isFinishing ? (
              <button
                type="button"
                className={styles.exitDialogClose}
                onClick={closeExitDialog}
                aria-label="Close">
                <XIcon />
              </button>
            ) : null}
            <div className={styles.exitDialogHeader}>
              <h2 id="exit-dialog-title" className={styles.exitDialogTitle}>
                Не удалось сохранить доску
              </h2>
              <p id="exit-dialog-description" className={styles.exitDialogDescription}>
                Можно завершить урок без сохранения доски или остаться и попробовать снова.
              </p>
            </div>
            <div className={styles.exitDialogFooter}>
              <Button variant="outline" disabled={isFinishing} onClick={closeExitDialog}>
                Остаться
              </Button>
              <Button disabled={isFinishing} onClick={() => void handleStopWithoutRecording()}>
                Выйти без сохранения
              </Button>
            </div>
          </div>
        </>
      ) : null}
    </PageFrame>
  );
}
