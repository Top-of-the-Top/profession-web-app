import React, { useEffect, useRef, useState } from 'react';
import { DefaultEditor } from 'react-simple-wysiwyg';
import { useLessonBuilderStore } from '../../model/store';
import type { Block, BlockType } from '../../model/types';
import { GRID_CELL_SIZE } from '../../lib/constants';
import styles from './CourseBuilder.module.css';

interface CourseBuilderProps {
  courseId: number;
}

const BLOCK_LABELS: Record<BlockType, string> = {
  text: 'Текст',
  photo: 'Фото',
  video: 'Видео',
};

export const CourseBuilder: React.FC<CourseBuilderProps> = ({ courseId }) => {
  const {
    layout,
    setTitle,
    addBlock,
    updateBlock,
    moveBlock,
    resizeBlock,
    toJSON,
  } = useLessonBuilderStore();

  const [isSaving, setIsSaving] = useState(false);
  const gridRef = useRef<HTMLDivElement | null>(null);
  const [collapsedEditors, setCollapsedEditors] = useState<Record<string, boolean>>({});

  type DragMode = 'move' | 'resize';

  const [dragState, setDragState] = useState<
    | {
        mode: DragMode;
        blockId: string;
        startClientX: number;
        startClientY: number;
        startX: number;
        startY: number;
        startW: number;
        startH: number;
      }
    | null
  >(null);

  useEffect(() => {
    if (!layout.blocks.length) return;

    setIsSaving(true);
    const timeoutId = window.setTimeout(() => {
      const json = toJSON();
      // временно просто выводим в консоль
      // eslint-disable-next-line no-console
      console.log('Lesson layout JSON for course', courseId, json);
      setIsSaving(false);
    }, 800);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [layout, toJSON, courseId]);

  useEffect(() => {
    const handleMove = (event: MouseEvent) => {
      if (!dragState || !gridRef.current) return;
      const deltaX = event.clientX - dragState.startClientX;
      const deltaY = event.clientY - dragState.startClientY;

      const dx = Math.round(deltaX / GRID_CELL_SIZE);
      const dy = Math.round(deltaY / GRID_CELL_SIZE);

      if (dragState.mode === 'move') {
        const nextX = dragState.startX + dx;
        const nextY = dragState.startY + dy;
        moveBlock(dragState.blockId, nextX, nextY);
      } else {
        const block = layout.blocks.find((b) => b.id === dragState.blockId);
        const isMedia = block?.type === 'photo' || block?.type === 'video';
        const minW = isMedia ? 2 : 1;
        const minH = isMedia ? 2 : 1;
        const nextW = Math.max(minW, dragState.startW + dx);
        const nextH = Math.max(minH, dragState.startH + dy);
        resizeBlock(dragState.blockId, nextW, nextH);
      }
    };

    const handleUp = () => {
      setDragState(null);
    };

    if (dragState) {
      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [dragState, moveBlock, resizeBlock]);

  const handleAddBlock = (type: BlockType) => {
    addBlock(type);
  };

  const startDrag = (mode: DragMode, block: Block, event: React.MouseEvent) => {
    event.stopPropagation();
    event.preventDefault();
    setDragState({
      mode,
      blockId: block.id,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: block.x,
      startY: block.y,
      startW: block.w,
      startH: block.h,
    });
  };

  const handleCourseTitleChange = (title: string) => {
    setTitle(title);
  };

  const handleTextChange = (blockId: string, html: string) => {
    updateBlock(blockId, { html } as Block);
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
        <div className={styles.blockBody}>
          {block.url && (
            <img 
              src={block.url} 
              alt="content" 
              className={styles.blockImage}
              onError={(e) => {
                e.currentTarget.src = 'https://via.placeholder.com/400x300?text=Ошибка+загрузки+изображения';
              }}
            />
          )}
          <input
            type="text"
            placeholder="URL изображения"
            className={styles.input}
            value={block.url ?? ''}
            onChange={(e) =>
              updateBlock(block.id, { url: e.target.value } as Block)
            }
          />
        </div>
      );
    }

    if (block.type === 'video') {
      return (
        <div className={styles.blockBody}>
          {block.url && (
            <div className={styles.videoWrapper}>
              <iframe
                src={block.url.replace('watch?v=', 'embed/')}
                title="video"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                className={styles.blockVideo}
              />
            </div>
          )}
          <input
            type="text"
            placeholder="URL видео"
            className={styles.input}
            value={block.url ?? ''}
            onChange={(e) =>
              updateBlock(block.id, { url: e.target.value } as Block)
            }
          />
        </div>
      );
    }

    return null;
  };

  return (
    <div className={styles.courseBuilder} dir="ltr">
      <div className={styles.header}>
        <input
          className={styles.titleInput}
          value={layout.title}
          onChange={(e) => handleCourseTitleChange(e.target.value)}
          placeholder="Название курса"
        />
        <div className={styles.toolbar}>
          <span className={`${styles.statusDot} ${isSaving ? styles.saving : ''}`} />
          <span>{isSaving ? 'Сериализация в консоль...' : 'Локальный черновик'}</span>
        </div>
      </div>

      <div className={styles.gridWrapper}>
        <div ref={gridRef} className={styles.gridInner}>
          {layout.blocks.map((block) => (
            <div
              key={block.id}
              className={`${styles.gridBlock} ${dragState?.blockId === block.id ? styles.dragging : ''}`}
              style={{
                left: block.x * GRID_CELL_SIZE,
                top: block.y * GRID_CELL_SIZE,
                width: block.w * GRID_CELL_SIZE,
                height: block.h * GRID_CELL_SIZE,
              }}
              dir="ltr"
            >
              <div
                className={styles.blockHeader}
                onMouseDown={(e) => startDrag('move', block, e)}
              >
                <span className={styles.blockType}>
                  {BLOCK_LABELS[block.type]}
                </span>
                {block.type === 'text' && (
                  <button
                    type="button"
                    className={styles.blockToggle}
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      setCollapsedEditors((prev) => {
                        const current = prev[block.id] ?? true;
                        return {
                          ...prev,
                          [block.id]: !current,
                        };
                      });
                    }}
                    aria-label="Свернуть/развернуть редактор"
                  >
                    {collapsedEditors[block.id] ?? true ? '▲' : '▼'}
                  </button>
                )}
              </div>
              {renderBlockBody(block)}
              <div
                className={styles.resizeHandle}
                onMouseDown={(e) => startDrag('resize', block, e)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className={styles.paletteBar}>
        <div className={styles.paletteButtons}>
          {(Object.keys(BLOCK_LABELS) as BlockType[]).map((type) => (
            <button
              key={type}
              type="button"
              className={styles.paletteButton}
              onClick={() => handleAddBlock(type)}
            >
              + {BLOCK_LABELS[type]}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={`${styles.button} ${styles.buttonPrimary}`}
          onClick={() => {
            const json = toJSON();
            // eslint-disable-next-line no-console
            console.log('Lesson layout JSON (manual dump):', json);
          }}
        >
          Вывести JSON в консоль
        </button>
      </div>
    </div>
  );
};