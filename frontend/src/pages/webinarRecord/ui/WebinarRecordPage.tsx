import { useParams, useSearchParams } from 'react-router-dom';
import { Spinner } from '@shared/ui';
import { useRecorderJoin } from '@shared/api/queries/webinar';
import { VideoGrid, WhiteboardPanel } from '../../../features/webinar';
import styles from './WebinarRecordPage.module.css';

export default function WebinarRecordPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const joinQuery = useRecorderJoin(courseSlug, lessonSlug, token);
  const { data: session, isLoading, isError } = joinQuery;

  if (!token) {
    return (
      <div className={styles.stateCenter}>
        <div className={styles.errorBox}>
          <p className={styles.errorTitle}>Нет токена записи</p>
          <p className={styles.errorText}>Ссылка на запись некорректна.</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.stateCenter}>
        <Spinner />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className={styles.stateCenter}>
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
    <div className={styles.shell}>
      <div className={styles.body}>
        <div className={styles.whiteboardArea}>
          <WhiteboardPanel
            appIdentifier={session.whiteboard_app_id}
            roomUUID={session.whiteboard_room_uuid}
            roomToken={session.whiteboard_room_token}
            region={session.whiteboard_region}
            uid={String(session.uid)}
            isWritable={false}
          />
        </div>

        <div className={styles.videoSidebar}>
          <VideoGrid
            appId={session.agora_app_id}
            token={session.rtc_token}
            channel={session.channel_name}
            uid={session.uid}
            subscribeOnly
          />
        </div>
      </div>
    </div>
  );
}
