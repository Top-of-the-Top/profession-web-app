import { useEffect } from 'react';
import { apiClient } from '@shared/api/interceptor';

const HEARTBEAT_INTERVAL_MS = 30_000;

export function useWebinarHeartbeat(webinarId: string | null | undefined, isActive: boolean) {
  useEffect(() => {
    if (!isActive || !webinarId) return;

    const tick = () => {
      apiClient
        .request<void>(`/api/statistics/webinars/${webinarId}/attendance/heartbeat/`, {
          method: 'POST',
        })
        .catch(() => {});
    };

    tick();
    const id = setInterval(tick, HEARTBEAT_INTERVAL_MS);
    return () => clearInterval(id);
  }, [webinarId, isActive]);
}
