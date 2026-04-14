import { useFastboard, Fastboard } from '@netless/fastboard-react';
import styles from './WhiteboardPanel.module.css';

type WhiteboardRegion = 'cn-hz' | 'us-sv' | 'sg' | 'in-mum' | 'eu';

interface WhiteboardPanelProps {
  appIdentifier: string;
  roomUUID: string;
  roomToken: string;
  region: string;
  uid: string;
  isWritable: boolean;
}

export function WhiteboardPanel({
  appIdentifier,
  roomUUID,
  roomToken,
  region,
  uid,
  isWritable,
}: WhiteboardPanelProps) {
  const fastboard = useFastboard(() => ({
    sdkConfig: {
      appIdentifier,
      region: (region || 'us-sv') as WhiteboardRegion,
    },
    joinRoom: {
      uid,
      uuid: roomUUID,
      roomToken,
      isWritable,
    },
    managerConfig: {
      cursor: true,
    },
  }));

  return (
    <div className={styles.container}>
      <Fastboard app={fastboard} />
    </div>
  );
}
