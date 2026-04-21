import { forwardRef, useImperativeHandle } from 'react';
import { useFastboard, Fastboard } from '@netless/fastboard-react';
import styles from './WhiteboardPanel.module.css';

type WhiteboardRegion = 'cn-hz' | 'us-sv' | 'sg' | 'in-mum' | 'eu';

export interface WhiteboardPanelHandle {
  captureSceneScreenshots(): Promise<Blob[]>;
}

interface WhiteboardPanelProps {
  appIdentifier: string;
  roomUUID: string;
  roomToken: string;
  region: string;
  uid: string;
  isWritable: boolean;
}

const CAPTURE_WIDTH = 1280;
const CAPTURE_HEIGHT = 720;

function buildScenePath(contextPath: string, sceneName: string): string {
  if (!contextPath || contextPath === '/') return `/${sceneName}`;
  return contextPath.endsWith('/')
    ? `${contextPath}${sceneName}`
    : `${contextPath}/${sceneName}`;
}

async function canvasToPng(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error('CANVAS_TO_BLOB_FAILED'));
      },
      'image/png',
    );
  });
}

export const WhiteboardPanel = forwardRef<
  WhiteboardPanelHandle,
  WhiteboardPanelProps
>(function WhiteboardPanel(
  { appIdentifier, roomUUID, roomToken, region, uid, isWritable },
  ref,
) {
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

  useImperativeHandle(
    ref,
    () => ({
      async captureSceneScreenshots(): Promise<Blob[]> {
        if (!fastboard) return [];
        const room = fastboard.room;
        const sceneState = room.state.sceneState;
        const scenes = sceneState.scenes;
        const contextPath = sceneState.contextPath;

        if (!scenes || scenes.length === 0) return [];

        const camera = { centerX: 0, centerY: 0, scale: 1 };
        const blobs: Blob[] = [];

        for (const scene of scenes) {
          const scenePath = buildScenePath(contextPath, scene.name);

          const canvas = document.createElement('canvas');
          canvas.width = CAPTURE_WIDTH;
          canvas.height = CAPTURE_HEIGHT;
          const ctx = canvas.getContext('2d');
          if (!ctx) continue;

          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, CAPTURE_WIDTH, CAPTURE_HEIGHT);

          await room.screenshotToCanvasAsync(
            ctx,
            scenePath,
            CAPTURE_WIDTH,
            CAPTURE_HEIGHT,
            camera,
            1,
            5_000,
          );

          const blob = await canvasToPng(canvas);
          blobs.push(blob);
        }

        return blobs;
      },
    }),
    [fastboard],
  );

  return (
    <div className={styles.container}>
      <Fastboard app={fastboard} />
    </div>
  );
});
