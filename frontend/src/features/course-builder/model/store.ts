import { create } from 'zustand';
import { nanoid } from 'nanoid';
import type { Block, BlockType, LessonLayout } from './types';
import { serializeLessonLayout } from './types';
import { makeStructureMediaPlaceholder } from '../api/courseBuilderApi';
import {
  GRID_COLS,
  GRID_ROWS,
  MIN_MEDIA_BLOCK_H,
  MIN_MEDIA_BLOCK_W,
  MIN_TEXT_BLOCK_H,
  MIN_TEXT_BLOCK_W,
  DEFAULT_FONT_SIZE_INDEX,
} from '../lib/constants';

export interface SubmitPayload {
  document: string;
  files: Record<string, File>;
}

interface LessonBuilderState {
  layout: LessonLayout;
  pendingFiles: Record<string, File>;
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

export const useLessonBuilderStore = create<LessonBuilderStore>((set, get) => ({
  layout: createEmptyLayout(),
  pendingFiles: {},

  initialize: (layout) =>
    set(() => ({
      layout,
      pendingFiles: {},
    })),

  setTitle: (title) =>
    set((state) => ({
      layout: { ...state.layout, title },
    })),

  addBlock: (type) =>
    set((state) => {
      const isMedia = type === 'photo' || type === 'video';
      const w = isMedia ? MIN_MEDIA_BLOCK_W : MIN_TEXT_BLOCK_W;
      const h = isMedia ? MIN_MEDIA_BLOCK_H : MIN_TEXT_BLOCK_H;

      // поиск первого свободного места w×h
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

  setBlockFile: (blockId, file) =>
    set((state) => {
      const previewUrl = URL.createObjectURL(file);
      return {
        pendingFiles: { ...state.pendingFiles, [blockId]: file },
        layout: {
          ...state.layout,
          blocks: state.layout.blocks.map((block) =>
            block.id === blockId
              ? ({ ...block, url: previewUrl } as Block)
              : block,
          ),
        },
      };
    }),

  removeBlock: (blockId) =>
    set((state) => {
      const { [blockId]: _removed, ...remainingFiles } = state.pendingFiles;
      return {
        pendingFiles: remainingFiles,
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
    const { layout, pendingFiles } = get();
    const serialized = serializeLessonLayout(layout);
    const blockAssetIds: Record<string, string> = {};
    const filesByAssetId: Record<string, File> = {};
    let nextAssetId = 1;

    for (const block of serialized.blocks) {
      if (
        (block.type === 'photo' || block.type === 'video') &&
        pendingFiles[block.id]
      ) {
        const assetId = String(nextAssetId);
        nextAssetId += 1;
        blockAssetIds[block.id] = assetId;
        filesByAssetId[assetId] = pendingFiles[block.id];
      }
    }

    const blocks = serialized.blocks.map((block) => {
      const assetId = blockAssetIds[block.id];
      if ((block.type === 'photo' || block.type === 'video') && assetId) {
        return { ...block, url: makeStructureMediaPlaceholder(assetId) };
      }
      return block;
    });

    return {
      document: JSON.stringify({ ...serialized, blocks }),
      files: filesByAssetId,
    };
  },
}));

