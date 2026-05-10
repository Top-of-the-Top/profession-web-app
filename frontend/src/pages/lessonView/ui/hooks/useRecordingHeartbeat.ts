import { type RefObject, useEffect, useRef } from 'react';
import { load } from '@kinescope/player-iframe-api-loader';
import { apiClient } from '@shared/api/interceptor';

const HEARTBEAT_INTERVAL_MS = 30_000;

interface UseRecordingHeartbeatOptions {
  recordingId: string | null | undefined;
  embedUrl: string | null | undefined;
  containerRef: RefObject<HTMLDivElement | null>;
}

export function useRecordingHeartbeat({
  recordingId,
  embedUrl,
  containerRef,
}: UseRecordingHeartbeatOptions) {
  const playerRef = useRef<Kinescope.IframePlayer.Player | null>(null);
  const isPlayingRef = useRef(false);
  const currentTimeRef = useRef(0);

  useEffect(() => {
    if (!embedUrl || !containerRef.current || !recordingId) return;

    const container = containerRef.current;
    let destroyed = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const sendHeartbeat = (currentTime: number) => {
      apiClient
        .request<void>(`/api/v1/statistics/recordings/${recordingId}/view/heartbeat/`, {
          method: 'POST',
          body: JSON.stringify({ current_position: Math.floor(currentTime) }),
        })
        .catch(() => {});
    };

    const startInterval = () => {
      if (intervalId) return;
      intervalId = setInterval(() => {
        if (isPlayingRef.current) {
          sendHeartbeat(currentTimeRef.current);
        }
      }, HEARTBEAT_INTERVAL_MS);
    };

    const stopInterval = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    load()
      .then((factory) => {
        if (destroyed) return;
        return factory.create(container, {
          url: embedUrl,
          size: { width: '100%', height: '100%' },
          playlist: [{ poster: `${window.location.origin}/poster.png` }],
        });
      })
      .then((player) => {
        if (!player || destroyed) {
          player?.destroy().catch(() => {});
          return;
        }

        playerRef.current = player;

        player.on(player.Events.Play, () => {
          isPlayingRef.current = true;
          sendHeartbeat(currentTimeRef.current);
          startInterval();
        });

        player.on(player.Events.Playing, () => {
          isPlayingRef.current = true;
          startInterval();
        });

        player.on(player.Events.Pause, () => {
          isPlayingRef.current = false;
          stopInterval();
        });

        player.on(player.Events.Ended, () => {
          isPlayingRef.current = false;
          stopInterval();
          sendHeartbeat(currentTimeRef.current);
        });

        player.on(player.Events.TimeUpdate, (e) => {
          currentTimeRef.current = e.data.currentTime;
        });
      })
      .catch(() => {});

    return () => {
      destroyed = true;
      isPlayingRef.current = false;
      stopInterval();
      const p = playerRef.current;
      playerRef.current = null;
      if (p) {
        p.destroy().catch(() => {});
      }
    };
  }, [embedUrl, recordingId]);
}
