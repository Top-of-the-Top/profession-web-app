import { useEffect, useMemo, useRef, type ReactNode } from 'react';
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
import { cn } from '@shared/lib/utils';
import { WEBINAR_RECORDER_RTC_UID, rtcTileLabel } from '../lib/rtcUidLabels';
import styles from './VideoGrid.module.css';

interface VideoGridBaseProps {
  appId: string;
  token: string;
  channel: string;
  uid: number;
  rtcUidToLabel?: Record<number, string>;
  onRecorderChannelPresence?: (present: boolean) => void;
  children?: ReactNode;
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

function ParticipantStripChrome({
  name,
  micMuted,
  audioMount,
}: {
  name: string;
  micMuted: boolean;
  audioMount: ReactNode;
}) {
  return (
    <div className={styles.observerStrip}>
      {audioMount}
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

function LocalParticipantStrip({
  name,
  micOn,
  cameraOn,
  localMicrophoneTrack,
  localCameraTrack,
}: {
  name: string;
  micOn: boolean;
  cameraOn: boolean;
  localMicrophoneTrack: ReturnType<typeof useLocalMicrophoneTrack>['localMicrophoneTrack'];
  localCameraTrack: ReturnType<typeof useLocalCameraTrack>['localCameraTrack'];
}) {
  return (
    <ParticipantStripChrome
      name={name}
      micMuted={!micOn}
      audioMount={
        <div className={styles.observerStripAudioMount}>
          <LocalUser
            audioTrack={localMicrophoneTrack}
            videoTrack={localCameraTrack}
            cameraOn={cameraOn}
            micOn={micOn}
            playAudio={false}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      }
    />
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
    <ParticipantStripChrome
      name={name}
      micMuted={micMuted}
      audioMount={
        <div className={styles.observerStripAudioMount}>
          <RemoteUser
            user={user}
            playVideo={false}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      }
    />
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
  // Memoize so useJoin doesn't see a new object every render and re-join.
  const joinOptions = useMemo(
    () => ({ appid: appId, channel, token, uid }),
    [appId, channel, token, uid],
  );
  useJoin(joinOptions, true);

  const { localMicrophoneTrack } = useLocalMicrophoneTrack(micOn);
  const { localCameraTrack } = useLocalCameraTrack(cameraOn);

  usePublish([localMicrophoneTrack, localCameraTrack]);

  // Release OS device locks on unmount so re-entering the webinar doesn't get
  // NOT_READABLE / "Device in use" on the next createCameraVideoTrack call.
  useEffect(() => {
    return () => {
      localMicrophoneTrack?.stop();
      localMicrophoneTrack?.close();
    };
  }, [localMicrophoneTrack]);

  useEffect(() => {
    return () => {
      localCameraTrack?.stop();
      localCameraTrack?.close();
    };
  }, [localCameraTrack]);

  const remoteUsers = useRemoteUsers();
  useNotifyRecorderPresence(remoteUsers, onRecorderChannelPresence);
  const visibleRemoteUsers = useMemo(
    () =>
      remoteUsers.filter(
        (u) => Number(u.uid) !== WEBINAR_RECORDER_RTC_UID,
      ),
    [remoteUsers],
  );
  const remotesWithVideo = useMemo(
    () => visibleRemoteUsers.filter((u) => u.hasVideo),
    [visibleRemoteUsers],
  );
  const remotesWithoutVideo = useMemo(
    () => visibleRemoteUsers.filter((u) => !u.hasVideo),
    [visibleRemoteUsers],
  );
  const videoTileCount = (cameraOn ? 1 : 0) + remotesWithVideo.length;
  const videoGridDense = videoTileCount > 3;
  const selfLabel = rtcTileLabel(uid, rtcUidToLabel, 'Вы');

  return (
    <div className={styles.grid}>
      <div
        className={
          videoGridDense ? styles.videoTilesGrid : styles.videoTilesStack
        }
      >
        {cameraOn ? (
          <div
            className={cn(
              styles.tile,
              videoGridDense && styles.tileCompact,
            )}
          >
            <LocalUser
              audioTrack={localMicrophoneTrack}
              videoTrack={localCameraTrack}
              cameraOn={cameraOn}
              micOn={micOn}
              playAudio={false}
              style={{ width: '100%', height: '100%' }}
            />
            <TileNameplate name={selfLabel} micMuted={!micOn} />
          </div>
        ) : null}

        {remotesWithVideo.map((user) => (
          <div
            key={user.uid}
            className={cn(
              styles.tile,
              videoGridDense && styles.tileCompact,
            )}
          >
            <RemoteUser
              user={user}
              playVideo
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

      {!cameraOn ? (
        <LocalParticipantStrip
          name={selfLabel}
          micOn={micOn}
          cameraOn={cameraOn}
          localMicrophoneTrack={localMicrophoneTrack}
          localCameraTrack={localCameraTrack}
        />
      ) : null}

      {remotesWithoutVideo.map((user) => (
        <ObserverRemoteAudioStrip
          key={user.uid}
          user={user}
          name={rtcTileLabel(user.uid, rtcUidToLabel, String(user.uid))}
        />
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
  const joinOptions = useMemo(
    () => ({ appid: appId, channel, token, uid }),
    [appId, channel, token, uid],
  );
  useJoin(joinOptions, true);

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

  const remotesWithVideoOnly = useMemo(
    () => visibleRemoteUsers.filter((u) => u.hasVideo),
    [visibleRemoteUsers],
  );
  const remotesWithoutVideoOnly = useMemo(
    () => visibleRemoteUsers.filter((u) => !u.hasVideo),
    [visibleRemoteUsers],
  );
  const observerVideoGridDense = remotesWithVideoOnly.length > 3;

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
      <div
        className={
          observerVideoGridDense
            ? styles.videoTilesGrid
            : styles.videoTilesStack
        }
      >
        {remotesWithVideoOnly.map((user) => {
          const name = rtcTileLabel(
            user.uid,
            rtcUidToLabel,
            String(user.uid),
          );
          return (
            <div
              key={user.uid}
              className={cn(
                styles.tile,
                observerVideoGridDense && styles.tileCompact,
              )}
            >
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
        })}
      </div>
      {remotesWithoutVideoOnly.map((user) => (
        <ObserverRemoteAudioStrip
          key={user.uid}
          user={user}
          name={rtcTileLabel(user.uid, rtcUidToLabel, String(user.uid))}
        />
      ))}
    </div>
  );
}

export function VideoGrid(props: VideoGridProps) {
  const clientRef = useRef<ReturnType<typeof AgoraRTC.createClient> | null>(null);
  if (!clientRef.current) {
    clientRef.current = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' });
  }
  const client = clientRef.current;

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
