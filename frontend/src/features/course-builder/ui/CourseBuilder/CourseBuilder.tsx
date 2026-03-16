import React, { useCallback, useEffect, useState } from 'react';
import { DefaultEditor } from 'react-simple-wysiwyg';
import { ImageUp, PictureInPicture } from 'lucide-react';
import GridLayout, { WidthProvider } from 'react-grid-layout';
import type { Layout, LayoutItem } from 'react-grid-layout';
import { useLessonBuilderStore } from '../../model/store';
import type { Block, BlockType } from '../../model/types';
import { GRID_COLS } from '../../lib/constants';
import styles from './CourseBuilder.module.css';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

interface CourseBuilderProps {
  courseId: number;
}

const BLOCK_LABELS: Record<BlockType, string> = {
  text: 'Текст',
  photo: 'Фото',
  video: 'Видео',
};

const ROW_HEIGHT = 80;
const GRID_ROWS_BASE = 50;
/** Фиксированная ширина сетки: один лейаут независимо от разрешения */
const GRID_FIXED_WIDTH = GRID_COLS * 80;

const FixedGridLayout = WidthProvider(GridLayout);

function blocksToLayout(blocks: Block[]): Layout {
  return blocks.map((b) => ({
    i: b.id,
    x: b.x,
    y: b.y,
    w: b.w,
    h: b.h,
  }));
}

export const CourseBuilder: React.FC<CourseBuilderProps> = ({ courseId }) => {
  const { layout, setTitle, addBlockAt, updateBlock, toJSON } =
    useLessonBuilderStore();

  const [mounted, setMounted] = useState(false);
  const [collapsedEditors, setCollapsedEditors] = useState<
    Record<string, boolean>
  >({});
  const [activeTab, setActiveTab] = useState<'layout' | 'homework'>('layout');

  useEffect(() => {
    setMounted(true);
  }, []);

  const gridLayout = blocksToLayout(layout.blocks);

  const onLayoutChange = useCallback(
    (currentLayout: Layout) => {
      layout.blocks.forEach((block) => {
        const item = currentLayout.find((l: LayoutItem) => l.i === block.id);
        if (!item) return;
        if (
          item.x !== block.x ||
          item.y !== block.y ||
          item.w !== block.w ||
          item.h !== block.h
        ) {
          updateBlock(block.id, {
            x: item.x,
            y: item.y,
            w: item.w,
            h: item.h,
          } as Partial<Block>);
        }
      });
    },
    [layout.blocks, updateBlock]
  );

  const onDrop = useCallback(
    (_layout: Layout, layoutItem: LayoutItem, ev: DragEvent) => {
      let type: BlockType = 'text';
      try {
        const raw = ev.dataTransfer?.getData('application/x-block-type');
        if (raw) type = JSON.parse(raw) as BlockType;
      } catch {
        // ignore
      }
      addBlockAt(type, layoutItem.x, layoutItem.y, layoutItem.w, layoutItem.h);
    },
    [addBlockAt]
  );

  const handleCourseTitleChange = (title: string) => setTitle(title);
  const handleTextChange = (blockId: string, html: string) =>
    updateBlock(blockId, { html } as Block);

  const createDragImage = (type: BlockType) => {
    const el = document.createElement('div');
    el.className = styles.dragPreview;
    el.innerHTML = `
      <div class="${styles.blockHeader}">
        <span class="${styles.blockType}">${BLOCK_LABELS[type]}</span>
      </div>
      <div class="${styles.dragPreviewBody}">
        ${type === 'text' ? 'Текстовый блок' : type === 'photo' ? 'Изображение' : 'Видео'}
      </div>
    `;
    el.style.position = 'absolute';
    el.style.top = '-9999px';
    el.style.left = '-9999px';
    document.body.appendChild(el);
    return el;
  };

  const handlePaletteDragStart = (type: BlockType, e: React.DragEvent) => {
    e.dataTransfer.setData('text/plain', '');
    e.dataTransfer.setData('application/x-block-type', JSON.stringify(type));
    e.dataTransfer.effectAllowed = 'copy';
    const node = createDragImage(type);
    if (node) {
      const rect = node.getBoundingClientRect();
      e.dataTransfer.setDragImage(node, Math.min(rect.width / 2, 80), 20);
      setTimeout(() => node.remove(), 0);
    }
  };

  const renderBlockBody = (block: Block) => {
    if (block.type === 'text') {
      const collapsed = collapsedEditors[block.id] ?? true;
      return (
        <div className={styles.blockBody} dir="ltr">
          <div
            className={`${styles.wysiwygEditor} ${
              collapsed ? styles.wysiwygEditorCollapsed : ''
            }`}
          >
            <DefaultEditor
              value={block.html || ''}
              onChange={(e) => handleTextChange(block.id, e.target.value)}
              tagName="p"
            />
          </div>
        </div>
      );
    }
    if (block.type === 'photo') {
      return (
        <div
          className={styles.blockBody}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <label
            htmlFor={`file-photo-${block.id}`}
            className={styles.uploadLabel}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              id={`file-photo-${block.id}`}
              type="file"
              accept="image/*"
              className={styles.fileInput}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () =>
                  updateBlock(block.id, {
                    url: reader.result as string,
                  } as Block);
                reader.readAsDataURL(file);
                e.target.value = '';
              }}
            />

            <div className={styles.uploadIconWrap}>
              {block.url ? (
                <>
                  <img
                    src={block.url}
                    alt=""
                    className={styles.blockImage}
                    onError={() => updateBlock(block.id, { url: '' } as Block)}
                  />
                </>
              ) : (
                <p>Загрузить фото</p>
              )}
              <ImageUp
                className={
                  block.url ? styles.uploadIconHidden : styles.uploadIcon
                }
                size={40}
                strokeWidth={1.5}
                aria-hidden
              />
            </div>
          </label>
        </div>
      );
    }
    if (block.type === 'video') {
      return (
        <div
          className={styles.blockBody}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <label
            htmlFor={`file-video-${block.id}`}
            className={styles.uploadLabel}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              id={`file-video-${block.id}`}
              type="file"
              accept="video/*"
              className={styles.fileInput}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () =>
                  updateBlock(block.id, {
                    url: reader.result as string,
                  } as Block);
                reader.readAsDataURL(file);
                e.target.value = '';
              }}
            />
            <div className={styles.uploadIconWrap}>
              {block.url ? (
                <video
                  src={block.url}
                  className={styles.blockVideoPreview}
                  controls
                  muted
                  playsInline
                />
              ) : (
                <p>Загрузить видео</p>
              )}
              <PictureInPicture
                className={
                  block.url ? styles.uploadIconHidden : styles.uploadIcon
                }
                size={40}
                strokeWidth={1.5}
                aria-hidden
              />
            </div>
          </label>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={styles.courseBuilder} dir="ltr">
      <div className={styles.lessonHeader}>
        <div className={styles.lessonHeaderTrapezoid}>
          <input
            className={styles.titleInput}
            value={layout.title}
            onChange={(e) => handleCourseTitleChange(e.target.value)}
            placeholder="Название урока"
          />
        </div>
      </div>

      <div className={styles.mainArea}>
        <div className={styles.sideTabs}>
          <button
            type="button"
            className={`${styles.sideTab} ${
              activeTab === 'layout' ? styles.sideTabActive : ''
            }`}
            onClick={() => setActiveTab('layout')}
          >
            конструктор
          </button>
          <button
            type="button"
            className={`${styles.sideTab} ${
              activeTab === 'homework' ? styles.sideTabActive : ''
            }`}
            onClick={() => setActiveTab('homework')}
          >
            домашнее задание
          </button>
        </div>

        <div className={styles.mainContent}>
          {activeTab === 'layout' && (
            <>
              <div className={styles.gridWrapper}>
                <div
                  className={styles.gridFixedWidth}
                  style={{ width: GRID_FIXED_WIDTH, minWidth: GRID_FIXED_WIDTH }}
                >
                  <FixedGridLayout
                    className={styles.gridLayout}
                    style={{
                      minHeight: GRID_ROWS_BASE * ROW_HEIGHT,
                      background: 'transparent',
                    }}
                    layout={gridLayout}
                    cols={GRID_COLS}
                    rowHeight={ROW_HEIGHT}
                    margin={[2, 2]}
                    measureBeforeMount={false}
                    useCSSTransforms={mounted}
                    compactType="vertical"
                    preventCollision={false}
                    onLayoutChange={onLayoutChange}
                    onDrop={onDrop}
                    isDroppable
                    droppingItem={{ i: '__drop__', x: 0, y: 0, w: 2, h: 2 }}
                    containerPadding={[0, 0]}
                  >
                    {layout.blocks.map((block) => (
                      <div
                        key={block.id}
                        className={styles.gridBlock}
                        dir="ltr"
                      >
                        <div className={styles.blockHeader}>
                          <span className={styles.blockType}>
                            {BLOCK_LABELS[block.type]}
                          </span>
                          {block.type === 'text' && (
                            <button
                              type="button"
                              className={styles.blockToggle}
                              onMouseDown={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                              }}
                              onClick={(e) => {
                                e.stopPropagation();
                                setCollapsedEditors((prev) => ({
                                  ...prev,
                                  [block.id]: !(prev[block.id] ?? true),
                                }));
                              }}
                              aria-label="Свернуть/развернуть редактор"
                            >
                              {(collapsedEditors[block.id] ?? true) ? '▲' : '▼'}
                            </button>
                          )}
                        </div>
                        {renderBlockBody(block)}
                      </div>
                    ))}
                  </FixedGridLayout>
                </div>
              </div>

              <div className={styles.paletteBar}>
                <div className={styles.paletteButtons}>
                  {(Object.keys(BLOCK_LABELS) as BlockType[]).map((type) => (
                    <div
                      key={type}
                      draggable
                      unselectable="on"
                      className={styles.paletteDraggable}
                      onDragStart={(e) => handlePaletteDragStart(type, e)}
                    >
                      + {BLOCK_LABELS[type]}
                    </div>
                  ))}
                </div>
                <div className={styles.ctaWrapper}>
                  <button
                    type="button"
                    className={`${styles.button} ${styles.buttonSecondary}`}
                    onClick={() => {
                      // eslint-disable-next-line no-console
                      console.log(
                        'Lesson layout JSON (manual dump):',
                        toJSON(),
                      );
                    }}
                  >
                    Сохранить черновик
                  </button>
                  <button
                    type="button"
                    className={`${styles.button} ${styles.buttonPrimary}`}
                    onClick={() => {
                      // eslint-disable-next-line no-console
                      console.log(
                        'Lesson layout JSON (manual dump):',
                        toJSON(),
                      );
                    }}
                  >
                    Опубликовать урок
                  </button>
                </div>
              </div>
            </>
          )}

          {activeTab === 'homework' && (
            <div className={styles.homeworkStub}>
              <h2 className={styles.homeworkTitle}>Конструктор домашнего задания</h2>
              <p className={styles.homeworkSubtitle}>
                Здесь скоро появится конструктор ДЗ для этого урока.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
