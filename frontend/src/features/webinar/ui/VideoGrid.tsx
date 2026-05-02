import { useEffect, useMemo, useRef } from 'react';
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
import { Mic, MicOff, VideoOff } from 'lucide-react';
import { WEBINAR_RECORDER_RTC_UID, rtcTileLabel } from '../lib/rtcUidLabels';
import styles from './VideoGrid.module.css';

interface VideoGridBaseProps {
  appId: string;
  token: string;
  channel: string;
  uid: number;
  rtcUidToLabel?: Record<number, string>;
  onRecorderChannelPresence?: (present: boolean) => void;
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
  onSubscribeOnlyAnyRemoteVideo?: (anyHasVideo: boolean) => void;
}

type VideoGridProps = VideoGridPublisherProps | VideoGridSubscribeOnlyProps;

type AgoraRemoteUser = ReturnType<typeof useRemoteUsers>[number];

function TileNameplate({ name, micMuted }: { name: string; micMuted: boolean }) {
  return (
    <span className={styles.label}>
      {micMuted ? (
        <MicOff className={styles.labelMicIcon} size={14} strokeWidth={2} aria-hidden />
      ) : null}
      <span className={styles.labelText}>{name}</span>
    </span>
  );
}

function RemoteNoVideoCover() {
  return (
    <div className={styles.cameraOff}>
      <VideoOff size={32} className={styles.icon} strokeWidth={2} aria-hidden />
    </div>
  );
}

function ObserverRemoteAudioStrip({
  user,
  name,
}: {
  user: AgoraRemoteUser;
  name: string;
}) {
  const micMuted = user.hasAudio === false;
  return (
    <div className={styles.observerStrip}>
      <div className={styles.observerStripAudioMount}>
        <RemoteUser
          user={user}
          playVideo={false}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
      <div className={styles.observerStripIcons} aria-hidden>
        <VideoOff size={18} className={styles.observerStripIcon} strokeWidth={2} />
        {micMuted ? (
          <MicOff size={18} className={styles.observerStripIcon} strokeWidth={2} />
        ) : (
          <Mic size={18} className={styles.observerStripIconOn} strokeWidth={2} />
        )}
      </div>
      <span className={styles.observerStripName}>{name}</span>
    </div>
  );
}

function useNotifyRecorderPresence(
  remoteUsers: ReturnType<typeof useRemoteUsers>,
  onRecorderChannelPresence: VideoGridBaseProps['onRecorderChannelPresence'],
) {
  const prevRef = useRef<boolean | null>(null);
  useEffect(() => {
    if (!onRecorderChannelPresence) return;
    const present = remoteUsers.some(
      (u) => Number(u.uid) === WEBINAR_RECORDER_RTC_UID,
    );
    if (prevRef.current === present) return;
    prevRef.current = present;
    onRecorderChannelPresence(present);
  }, [remoteUsers, onRecorderChannelPresence]);
}

interface PublisherInnerProps extends VideoGridBaseProps {
  micOn: boolean;
  cameraOn: boolean;
}

function PublisherInner({
  appId,
  token,
  channel,
  uid,
  rtcUidToLabel,
  onRecorderChannelPresence,
  micOn,
  cameraOn,
}: PublisherInnerProps) {
  useJoin({ appid: appId, channel, token, uid }, true);

  const { localMicrophoneTrack } = useLocalMicrophoneTrack(micOn);
  const { localCameraTrack } = useLocalCameraTrack(cameraOn);

  usePublish([localMicrophoneTrack, localCameraTrack]);

  const remoteUsers = useRemoteUsers();
  useNotifyRecorderPresence(remoteUsers, onRecorderChannelPresence);
  const visibleRemoteUsers = useMemo(
    () =>
      remoteUsers.filter(
        (u) => Number(u.uid) !== WEBINAR_RECORDER_RTC_UID,
      ),
    [remoteUsers],
  );
  const selfLabel = rtcTileLabel(uid, rtcUidToLabel, 'Вы');

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
          {!cameraOn ? <RemoteNoVideoCover /> : null}
        </LocalUser>

        <TileNameplate name={selfLabel} micMuted={!micOn} />
      </div>

      {visibleRemoteUsers.map((user) => (
        <div key={user.uid} className={styles.tile}>
          <RemoteUser
            user={user}
            playVideo={user.hasVideo}
            cover={() => <RemoteNoVideoCover />}
            style={{ width: '100%', height: '100%' }}
          />
          <TileNameplate
            name={rtcTileLabel(user.uid, rtcUidToLabel, String(user.uid))}
            micMuted={user.hasAudio === false}
          />
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
  rtcUidToLabel,
  onRecorderChannelPresence,
  onSubscribeOnlyAnyRemoteVideo,
}: VideoGridBaseProps & {
  onSubscribeOnlyAnyRemoteVideo?: (anyHasVideo: boolean) => void;
}) {
  useJoin({ appid: appId, channel, token, uid }, true);

  const remoteUsers = useRemoteUsers();
  useNotifyRecorderPresence(remoteUsers, onRecorderChannelPresence);
  const visibleRemoteUsers = useMemo(
    () =>
      remoteUsers.filter(
        (u) => Number(u.uid) !== WEBINAR_RECORDER_RTC_UID,
      ),
    [remoteUsers],
  );

  const anyRemoteHasVideo = useMemo(
    () => visibleRemoteUsers.some((u) => u.hasVideo),
    [visibleRemoteUsers],
  );

  useEffect(() => {
    onSubscribeOnlyAnyRemoteVideo?.(anyRemoteHasVideo);
  }, [anyRemoteHasVideo, onSubscribeOnlyAnyRemoteVideo]);

  if (!anyRemoteHasVideo) {
    return (
      <div className={styles.gridObserverAudioOnly}>
        {visibleRemoteUsers.map((user) => (
          <div key={user.uid} className={styles.observerHiddenAudioMount}>
            <RemoteUser
              user={user}
              playVideo={false}
              style={{ width: '100%', height: '100%' }}
            />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.gridObserver}>
      {visibleRemoteUsers.map((user) => {
        const name = rtcTileLabel(user.uid, rtcUidToLabel, String(user.uid));
        if (user.hasVideo) {
          return (
            <div key={user.uid} className={styles.tile}>
              <RemoteUser
                user={user}
                playVideo
                cover={() => <RemoteNoVideoCover />}
                style={{ width: '100%', height: '100%' }}
              />
              <TileNameplate
                name={name}
                micMuted={user.hasAudio === false}
              />
            </div>
          );
        }
        return (
          <ObserverRemoteAudioStrip key={user.uid} user={user} name={name} />
        );
      })}
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
          rtcUidToLabel={props.rtcUidToLabel}
          onRecorderChannelPresence={props.onRecorderChannelPresence}
          onSubscribeOnlyAnyRemoteVideo={props.onSubscribeOnlyAnyRemoteVideo}
        />
      ) : (
        <PublisherInner
          appId={props.appId}
          token={props.token}
          channel={props.channel}
          uid={props.uid}
          rtcUidToLabel={props.rtcUidToLabel}
          onRecorderChannelPresence={props.onRecorderChannelPresence}
          micOn={props.micOn}
          cameraOn={props.cameraOn}
        />
      )}
    </AgoraRTCProvider>
  );
}
