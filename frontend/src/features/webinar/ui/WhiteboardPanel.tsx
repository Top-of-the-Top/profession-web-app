import { forwardRef, useImperativeHandle } from 'react';
import { useFastboard, Fastboard } from '@netless/fastboard-react';
import type { View } from 'white-web-sdk';
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
  userName?: string;
  isWritable: boolean;
}

const CAPTURE_WIDTH = 1280;
const CAPTURE_HEIGHT = 720;

const WB_CAPTURE_LOG = '[whiteboard capture]';

function logCapture(...args: unknown[]) {
  console.log(WB_CAPTURE_LOG, ...args);
}

function warnCapture(...args: unknown[]) {
  console.warn(WB_CAPTURE_LOG, ...args);
}

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

type RoomSceneState = {
  state: {
    sceneState: {
      scenes: Array<{ name: string }>;
      contextPath: string;
      scenePath: string;
    };
  };
};

async function captureScene(
  mainView: View,
  scenePath: string,
): Promise<Blob | null> {
  const camera = mainView.camera;
  const { width: viewW, height: viewH } = mainView.size;
  const width = viewW > 0 ? viewW : CAPTURE_WIDTH;
  const height = viewH > 0 ? viewH : CAPTURE_HEIGHT;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  if (!ctx) {
    warnCapture('captureScene: no canvas 2d context', { scenePath });
    return null;
  }

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);

  await mainView.screenshotToCanvasAsync(
    ctx,
    scenePath,
    width,
    height,
    {
      centerX: camera.centerX,
      centerY: camera.centerY,
      scale: camera.scale,
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
  { appIdentifier, roomUUID, roomToken, region, uid, userName, isWritable },
  ref,
) {
  const userPayload =
    userName && userName.trim().length > 0
      ? { name: userName, user_name: userName }
      : undefined;

  const fastboard = useFastboard(() => ({
    sdkConfig: {
      appIdentifier,
      region: (region || 'us-sv') as WhiteboardRegion,
    },
    joinRoom: {
      uid,
      uuid: roomUUID,
      roomToken,
      userPayload,
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
        logCapture('captureSceneScreenshots: start');
        if (!fastboard) {
          warnCapture('captureSceneScreenshots: fastboard is null');
          return [];
        }
        const mainView = fastboard.manager.mainView;
        const room = fastboard.room as unknown as RoomSceneState;
        const sceneState = room.state.sceneState;
        const scenes = sceneState.scenes;
        const contextPath = sceneState.contextPath;

        logCapture('captureSceneScreenshots: sceneState', {
          contextPath,
          scenePath: sceneState.scenePath,
          sceneCount: scenes?.length ?? 0,
          sceneNames: scenes?.map((s) => s.name) ?? [],
          viaMainView: true,
        });

        if (!scenes || scenes.length === 0) {
          warnCapture('captureSceneScreenshots: no scenes in state');
          return [];
        }

        const blobs: Blob[] = [];

        for (const scene of scenes) {
          const scenePath = buildScenePath(contextPath, scene.name);
          try {
            const blob = await captureScene(mainView, scenePath);
            if (blob) {
              blobs.push(blob);
              logCapture('scene ok', { scenePath, blobSize: blob.size });
            } else {
              warnCapture('scene returned null blob', { scenePath });
            }
          } catch (error) {
            warnCapture('scene failed', { scenePath, error });
          }
        }

        if (blobs.length === 0 && sceneState.scenePath) {
          logCapture('fallback: current scenePath', {
            scenePath: sceneState.scenePath,
          });
          try {
            const fallbackBlob = await captureScene(
              mainView,
              sceneState.scenePath,
            );
            if (fallbackBlob) {
              blobs.push(fallbackBlob);
              logCapture('fallback ok', { blobSize: fallbackBlob.size });
            } else {
              warnCapture('fallback returned null blob');
            }
          } catch (error) {
            warnCapture('fallback failed', { error });
          }
        }

        const totalBytes = blobs.reduce((n, b) => n + b.size, 0);
        logCapture('captureSceneScreenshots: done', {
          blobCount: blobs.length,
          totalBytes,
        });

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
