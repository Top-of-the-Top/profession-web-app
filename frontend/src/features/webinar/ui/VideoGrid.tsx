import { useMemo } from 'react';
import AgoraRTC, {
  AgoraRTCProvider,
  LocalUser,
  RemoteUser,
  useJoin,
  useLocalMicrophoneTrack,
  useLocalCameraTrack,
  usePublish,
  useRemoteUsers,
} from 'agora-rtc-react';
import { cn } from '@shared/lib/utils';
import { MicOff, VideoOff } from 'lucide-react';
import styles from './VideoGrid.module.css';

interface VideoGridBaseProps {
  appId: string;
  token: string;
  channel: string;
  uid: number;
}

interface VideoGridPublisherProps extends VideoGridBaseProps {
  micOn: boolean;
  cameraOn: boolean;
  subscribeOnly?: false;
}

interface VideoGridSubscribeOnlyProps extends VideoGridBaseProps {
  subscribeOnly: true;
  micOn?: never;
  cameraOn?: never;
}

type VideoGridProps = VideoGridPublisherProps | VideoGridSubscribeOnlyProps;

interface PublisherInnerProps extends VideoGridBaseProps {
  micOn: boolean;
  cameraOn: boolean;
}

function PublisherInner({
  appId,
  token,
  channel,
  uid,
  micOn,
  cameraOn,
}: PublisherInnerProps) {
  useJoin({ appid: appId, channel, token, uid }, true);

  const { localMicrophoneTrack } = useLocalMicrophoneTrack(micOn);
  const { localCameraTrack } = useLocalCameraTrack(cameraOn);

  usePublish([localMicrophoneTrack, localCameraTrack]);

  const remoteUsers = useRemoteUsers();

  return (
    <div className={styles.grid}>
      <div className={styles.tile}>
        <LocalUser
          audioTrack={localMicrophoneTrack}
          videoTrack={localCameraTrack}
          cameraOn={cameraOn}
          micOn={micOn}
          playAudio={false}
          style={{ width: '100%', height: '100%' }}
        >
          {!cameraOn && (
            <div className={styles.cameraOff}>
              <VideoOff
                size={32}
                className={cn(styles.cameraOffIcon, styles.icon)}
              />
              {micOn ? (
                <span className={styles.label}>Вы</span>
              ) : (
                <span className={styles.label}>
                  <MicOff className={cn(styles.micOffIcon, styles.icon)} />
                </span>
              )}
            </div>
          )}
        </LocalUser>

        {micOn ? (
          <span className={styles.label}>Вы</span>
        ) : (
          <span className={styles.label}>
            <MicOff className={cn(styles.micOffIcon, styles.icon)} />
          </span>
        )}
      </div>

      {remoteUsers.map((user) => (
        <div key={user.uid} className={styles.tile}>
          <RemoteUser user={user} style={{ width: '100%', height: '100%' }} />
          <span className={styles.label}>{user.uid}</span>
        </div>
      ))}
    </div>
  );
}

function SubscribeOnlyInner({
  appId,
  token,
  channel,
  uid,
}: VideoGridBaseProps) {
  useJoin({ appid: appId, channel, token, uid }, true);

  const remoteUsers = useRemoteUsers();

  return (
    <div className={styles.grid}>
      {remoteUsers.map((user) => (
        <div key={user.uid} className={styles.tile}>
          <RemoteUser user={user} style={{ width: '100%', height: '100%' }} />
          <span className={styles.label}>{user.uid}</span>
        </div>
      ))}
    </div>
  );
}

export function VideoGrid(props: VideoGridProps) {
  const client = useMemo(
    () => AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' }),
    []
  );

  return (
    <AgoraRTCProvider client={client}>
      {props.subscribeOnly ? (
        <SubscribeOnlyInner
          appId={props.appId}
          token={props.token}
          channel={props.channel}
          uid={props.uid}
        />
      ) : (
        <PublisherInner
          appId={props.appId}
          token={props.token}
          channel={props.channel}
          uid={props.uid}
          micOn={props.micOn}
          cameraOn={props.cameraOn}
        />
      )}
    </AgoraRTCProvider>
  );
}
