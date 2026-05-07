import { create } from 'zustand';
import { nanoid } from 'nanoid';
import type { Block, BlockType, LessonLayout, PhotoBlock, VideoBlock } from './types';
import { serializeLessonLayout } from './types';
import {
  uploadMediaAsset,
  assetUri,
  MediaUploadError,
} from '@shared/lib/uploads/uploadMediaAsset';
import {
  IntentValidationError,
} from '@shared/lib/uploads/intentLimits';
import type { MediaIntent } from '@shared/api/uploadsApi';
import {
  GRID_COLS,
  GRID_ROWS,
  MIN_MEDIA_BLOCK_H,
  MIN_MEDIA_BLOCK_W,
  MIN_TEXT_BLOCK_H,
  MIN_TEXT_BLOCK_W,
  DEFAULT_FONT_SIZE_INDEX,
} from '../lib/constants';

export type PendingUploadPhase = 'uploading' | 'ready' | 'error';

export interface PendingUpload {
  phase: PendingUploadPhase;
  file?: File;
  blobUrl?: string;
  assetId?: string;
  errorMessage?: string;
  progressPercent?: number;
}

export interface SubmitPayload {
  document: string;
}

interface LessonBuilderState {
  layout: LessonLayout;
  pendingUploads: Record<string, PendingUpload>;
}

interface LessonBuilderActions {
  initialize: (layout: LessonLayout) => void;
  setTitle: (title: string) => void;
  addBlock: (type: BlockType) => void;
  addBlockAt: (type: BlockType, x: number, y: number, w: number, h: number) => void;
  updateBlock: (blockId: string, patch: Partial<Block>) => void;
  setBlockFile: (blockId: string, file: File) => void;
  removeBlock: (blockId: string) => void;
  moveBlock: (blockId: string, x: number, y: number) => void;
  resizeBlock: (blockId: string, w: number, h: number) => void;
  toJSON: () => LessonLayout;
  toSubmitPayload: () => SubmitPayload;
  hasPendingUploads: () => boolean;
}

export type LessonBuilderStore = LessonBuilderState & LessonBuilderActions;

const createEmptyLayout = (): LessonLayout => ({
  id: nanoid(),
  title: 'Новый урок',
  blocks: [],
});

const rectsIntersect = (a: Block, b: Block): boolean => {
  if (a.id === b.id) return false;
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  );
};

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

function intentForBlock(type: 'photo' | 'video'): MediaIntent {
  return type === 'video' ? 'lesson_video' : 'lesson_image';
}

function revokeBlobUrl(url: string | undefined): void {
  if (url && url.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
}

export const useLessonBuilderStore = create<LessonBuilderStore>((set, get) => ({
  layout: createEmptyLayout(),
  pendingUploads: {},

  initialize: (layout) => {
    const prev = get().pendingUploads;
    Object.values(prev).forEach((entry) => revokeBlobUrl(entry.blobUrl));
    set(() => ({
      layout,
      pendingUploads: {},
    }));
  },

  setTitle: (title) =>
    set((state) => ({
      layout: { ...state.layout, title },
    })),

  addBlock: (type) =>
    set((state) => {
      const isMedia = type === 'photo' || type === 'video';
      const w = isMedia ? MIN_MEDIA_BLOCK_W : MIN_TEXT_BLOCK_W;
      const h = isMedia ? MIN_MEDIA_BLOCK_H : MIN_TEXT_BLOCK_H;

      let targetX = 0;
      let targetY = 0;
      outer: for (let y = 0; y <= GRID_ROWS - h; y += 1) {
        for (let x = 0; x <= GRID_COLS - w; x += 1) {
          const candidate: Block = {
            id: '__probe__',
            type,
            x,
            y,
            w,
            h,
            ...(type === 'text' ? { html: '' } : { url: '' }),
          } as Block;

          const hasCollision = state.layout.blocks.some((other) =>
            rectsIntersect(candidate, other as Block),
          );
          if (!hasCollision) {
            targetX = x;
            targetY = y;
            break outer;
          }
        }
      }

      const newBlock: Block =
        type === 'text'
          ? {
              id: nanoid(),
              type: 'text',
              x: targetX,
              y: targetY,
              w,
              h,
              html: '',
              fontSizeIndex: DEFAULT_FONT_SIZE_INDEX,
            }
          : {
              id: nanoid(),
              type,
              x: targetX,
              y: targetY,
              w,
              h,
              url: '',
            };

      return {
        layout: { ...state.layout, blocks: [...state.layout.blocks, newBlock] },
      };
    }),

  addBlockAt: (type, x, y, w, h) =>
    set((state) => {
      const isMedia = type === 'photo' || type === 'video';
      const minW = isMedia ? MIN_MEDIA_BLOCK_W : MIN_TEXT_BLOCK_W;
      const minH = isMedia ? MIN_MEDIA_BLOCK_H : MIN_TEXT_BLOCK_H;
      const clampedW = clamp(w, minW, GRID_COLS);
      const clampedH = clamp(h, minH, GRID_ROWS);
      const clampedX = clamp(x, 0, GRID_COLS - clampedW);
      const clampedY = clamp(y, 0, GRID_ROWS - clampedH);

      const newBlock: Block =
        type === 'text'
          ? {
              id: nanoid(),
              type: 'text',
              x: clampedX,
              y: clampedY,
              w: clampedW,
              h: clampedH,
              html: '',
              fontSizeIndex: DEFAULT_FONT_SIZE_INDEX,
            }
          : {
              id: nanoid(),
              type,
              x: clampedX,
              y: clampedY,
              w: clampedW,
              h: clampedH,
              url: '',
            };

      return {
        layout: { ...state.layout, blocks: [...state.layout.blocks, newBlock] },
      };
    }),

  updateBlock: (blockId, patch) =>
    set((state) => ({
      layout: {
        ...state.layout,
        blocks: state.layout.blocks.map((block) =>
          block.id === blockId ? ({ ...block, ...(patch as Block) } as Block) : block,
        ),
      },
    })),

  setBlockFile: (blockId, file) => {
    const state = get();
    const block = state.layout.blocks.find((b) => b.id === blockId);
    if (!block || (block.type !== 'photo' && block.type !== 'video')) return;

    const previousEntry = state.pendingUploads[blockId];
    revokeBlobUrl(previousEntry?.blobUrl);

    const blobUrl = URL.createObjectURL(file);
    const intent = intentForBlock(block.type);

    set((current) => ({
      pendingUploads: {
        ...current.pendingUploads,
        [blockId]: { phase: 'uploading', file, blobUrl },
      },
      layout: {
        ...current.layout,
        blocks: current.layout.blocks.map((b) =>
          b.id === blockId
            ? ({ ...(b as PhotoBlock | VideoBlock), url: blobUrl, assetId: undefined } as Block)
            : b,
        ),
      },
    }));

    void uploadMediaAsset(intent, file, {
      onProgress: (event) => {
        if (event.phase !== 'uploading') return;
        const percent = event.progressPercent;
        if (percent == null) return;
        const latest = get();
        const entry = latest.pendingUploads[blockId];
        if (!entry || entry.blobUrl !== blobUrl) return;
        set((current) => ({
          pendingUploads: {
            ...current.pendingUploads,
            [blockId]: {
              ...current.pendingUploads[blockId],
              phase: 'uploading',
              progressPercent: percent,
            },
          },
        }));
      },
    })
      .then(({ assetId }) => {
        const latest = get();
        if (latest.pendingUploads[blockId]?.blobUrl !== blobUrl) {
          return;
        }
        set((current) => ({
          pendingUploads: {
            ...current.pendingUploads,
            [blockId]: { phase: 'ready', file, blobUrl, assetId, progressPercent: 100 },
          },
          layout: {
            ...current.layout,
            blocks: current.layout.blocks.map((b) =>
              b.id === blockId
                ? ({ ...(b as PhotoBlock | VideoBlock), assetId } as Block)
                : b,
            ),
          },
        }));
      })
      .catch((err: unknown) => {
        const latest = get();
        if (latest.pendingUploads[blockId]?.blobUrl !== blobUrl) {
          return;
        }
        const message =
          err instanceof IntentValidationError || err instanceof MediaUploadError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Не удалось загрузить файл.';
        set((current) => ({
          pendingUploads: {
            ...current.pendingUploads,
            [blockId]: {
              phase: 'error',
              file,
              blobUrl,
              errorMessage: message,
            },
          },
        }));
      });
  },

  removeBlock: (blockId) =>
    set((state) => {
      const remainingUploads = { ...state.pendingUploads };
      const removed = remainingUploads[blockId];
      delete remainingUploads[blockId];
      revokeBlobUrl(removed?.blobUrl);
      return {
        pendingUploads: remainingUploads,
        layout: {
          ...state.layout,
          blocks: state.layout.blocks.filter((block) => block.id !== blockId),
        },
      };
    }),

  moveBlock: (blockId, x, y) =>
    set((state) => {
      const blocks = state.layout.blocks.map((block) => {
        if (block.id !== blockId) return block;

        const clampedX = clamp(x, 0, GRID_COLS - block.w);
        const clampedY = clamp(y, 0, GRID_ROWS - block.h);
        const candidate: Block = { ...block, x: clampedX, y: clampedY };

        const hasCollision = state.layout.blocks.some((other) =>
          rectsIntersect(candidate, other as Block),
        );

        return hasCollision ? block : candidate;
      });

      return { layout: { ...state.layout, blocks } };
    }),

  resizeBlock: (blockId, w, h) =>
    set((state) => {
      const blocks = state.layout.blocks.map((block) => {
        if (block.id !== blockId) return block;

        const isMedia = block.type === 'photo' || block.type === 'video';
        const minW = isMedia ? MIN_MEDIA_BLOCK_W : MIN_TEXT_BLOCK_W;
        const minH = isMedia ? MIN_MEDIA_BLOCK_H : MIN_TEXT_BLOCK_H;

        const clampedW = clamp(w, minW, GRID_COLS - block.x);
        const clampedH = clamp(h, minH, GRID_ROWS - block.y);

        const candidate: Block = { ...block, w: clampedW, h: clampedH };

        const hasCollision = state.layout.blocks.some((other) =>
          rectsIntersect(candidate, other as Block),
        );

        return hasCollision ? block : candidate;
      });

      return { layout: { ...state.layout, blocks } };
    }),

  toJSON: () => {
    const { layout } = get();
    return serializeLessonLayout(layout);
  },

  toSubmitPayload: () => {
    const { layout } = get();
    const serialized = serializeLessonLayout(layout);

    const blocks = serialized.blocks.map((block) => {
      if (block.type !== 'photo' && block.type !== 'video') return block;
      const mediaBlock = block as PhotoBlock | VideoBlock;
      if (mediaBlock.assetId) {
        return { ...mediaBlock, url: assetUri(mediaBlock.assetId) };
      }
      return block;
    });

    return {
      document: JSON.stringify({ ...serialized, blocks }),
    };
  },

  hasPendingUploads: () => {
    const uploads = get().pendingUploads;
    return Object.values(uploads).some((entry) => entry.phase === 'uploading');
  },
}));
