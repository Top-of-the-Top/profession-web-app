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
import { VideoOff } from 'lucide-react';
import styles from './VideoGrid.module.css';

interface VideoGridInnerProps {
  appId: string;
  token: string;
  channel: string;
  uid: number;
  micOn: boolean;
  cameraOn: boolean;
}

function VideoGridInner({ appId, token, channel, uid, micOn, cameraOn }: VideoGridInnerProps) {
  useJoin(
    { appid: appId, channel, token, uid },
    true,
  );

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
              <VideoOff size={32} className={styles.cameraOffIcon} />
            </div>
          )}
        </LocalUser>
        <span className={styles.label}>Вы</span>
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

interface VideoGridProps {
  appId: string;
  token: string;
  channel: string;
  uid: number;
  micOn: boolean;
  cameraOn: boolean;
}

export function VideoGrid({ appId, token, channel, uid, micOn, cameraOn }: VideoGridProps) {
  const client = useMemo(
    () => AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' }),
    [],
  );

  return (
    <AgoraRTCProvider client={client}>
      <VideoGridInner
        appId={appId}
        token={token}
        channel={channel}
        uid={uid}
        micOn={micOn}
        cameraOn={cameraOn}
      />
    </AgoraRTCProvider>
  );
}
