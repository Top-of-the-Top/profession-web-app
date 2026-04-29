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

type RoomLike = {
  state: {
    sceneState: {
      scenes: Array<{ name: string }>;
      contextPath: string;
      scenePath: string;
    };
    cameraState: {
      centerX: number;
      centerY: number;
      scale: number;
      width?: number;
      height?: number;
    };
  };
  screenshotToCanvasAsync: (
    context: CanvasRenderingContext2D,
    scenePath: string,
    width: number,
    height: number,
    camera: { centerX: number; centerY: number; scale: number },
    ratio?: number,
    timeout?: number,
  ) => Promise<void>;
};

async function captureScene(room: RoomLike, scenePath: string): Promise<Blob | null> {
  const cameraState = room.state.cameraState;
  const width = cameraState.width && cameraState.width > 0 ? cameraState.width : CAPTURE_WIDTH;
  const height = cameraState.height && cameraState.height > 0 ? cameraState.height : CAPTURE_HEIGHT;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  await room.screenshotToCanvasAsync(
    ctx,
    scenePath,
    width,
    height,
    {
      centerX: cameraState.centerX,
      centerY: cameraState.centerY,
      scale: cameraState.scale,
    },
    1,
    5_000,
  );

  return canvasToPng(canvas);
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
        const room = fastboard.room as unknown as RoomLike;
        const sceneState = room.state.sceneState;
        const scenes = sceneState.scenes;
        const contextPath = sceneState.contextPath;

        if (!scenes || scenes.length === 0) return [];

        const blobs: Blob[] = [];

        for (const scene of scenes) {
          const scenePath = buildScenePath(contextPath, scene.name);
          try {
            const blob = await captureScene(room, scenePath);
            if (blob) blobs.push(blob);
          } catch {}
        }

        if (blobs.length === 0 && sceneState.scenePath) {
          try {
            const fallbackBlob = await captureScene(room, sceneState.scenePath);
            if (fallbackBlob) blobs.push(fallbackBlob);
          } catch {}
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
