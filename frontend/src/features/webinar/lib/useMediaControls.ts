import { useCallback, useState } from 'react';

export function useMediaControls(initialMic = true, initialCamera = true) {
  const [micOn, setMicOn] = useState(initialMic);
  const [cameraOn, setCameraOn] = useState(initialCamera);

  const toggleMic = useCallback(() => setMicOn((v) => !v), []);
  const toggleCamera = useCallback(() => setCameraOn((v) => !v), []);

  return { micOn, cameraOn, toggleMic, toggleCamera } as const;
}
