export const WEBINAR_RECORDER_RTC_UID = 999999;

export function buildRtcUidLabelMap(params: {
  uid: number;
  userName: string;
  includeRecorderSlot?: boolean;
}): Record<number, string> {
  const ownLabel = params.userName?.trim() || String(params.uid);
  const map: Record<number, string> = { [params.uid]: ownLabel };
  if (params.includeRecorderSlot) {
    map[WEBINAR_RECORDER_RTC_UID] = 'Recorder';
  }
  return map;
}

export function rtcTileLabel(
  rtcUid: number | string,
  map: Record<number, string> | undefined,
  fallback: string,
): string {
  const n = typeof rtcUid === 'number' ? rtcUid : Number(rtcUid);
  if (!Number.isFinite(n)) {
    return fallback;
  }
  const hit = map?.[n];
  return hit !== undefined && hit !== '' ? hit : fallback;
}
