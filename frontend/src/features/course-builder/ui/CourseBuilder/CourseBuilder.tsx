import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ImageUp, PictureInPicture, Trash2 } from 'lucide-react';
import GridLayout from 'react-grid-layout';
import type { Layout, LayoutItem } from 'react-grid-layout';
import { useLessonBuilderStore } from '../../model/store';
import type { SubmitPayload } from '../../model/store';
import type { Block, BlockType } from '../../model/types';
import { serializeCoursePage } from '../../model/types';
import {
  DEFAULT_FONT_SIZE_INDEX,
  FONT_SIZE_STEPS,
  GRID_CELL_SIZE,
  GRID_COLS,
} from '../../lib/constants';
import { HomeworkBuilder } from '../HomeworkBuilder';
import { useHomeworkStore } from '../../model/homeworkStore';
import type { LessonHomework } from '@shared/api/courseApi';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
  RichTextEditor,
} from '@shared/ui';
import styles from './CourseBuilder.module.css';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

interface CourseBuilderProps {
  courseSlug: string;
  lessonSlug: string;
  lessonHomeworks: LessonHomework[];
  onSave: (payload: SubmitPayload) => void;
  saving?: boolean;
}

const BLOCK_LABELS: Record<BlockType, string> = {
  text: 'Текст',
  photo: 'Фото',
  video: 'Видео',
};

const GRID_GAP = 2;
const ROW_HEIGHT = GRID_CELL_SIZE;
const GRID_ROWS_BASE = 50;
const GRID_FIXED_WIDTH = GRID_COLS * GRID_CELL_SIZE + (GRID_COLS - 1) * GRID_GAP;
const GRID_MIN_HEIGHT = GRID_ROWS_BASE * ROW_HEIGHT + (GRID_ROWS_BASE - 1) * GRID_GAP;
const TITLE_CENTER_MIN_WIDTH = 130;
const TITLE_CENTER_MAX_WIDTH = 560;


function blocksToLayout(blocks: Block[]): Layout {
  return blocks.map((b) => ({
    i: b.id,
    x: b.x,
    y: b.y,
    w: b.w,
    h: b.h,
  }));
}

function sanitizeRichTextHtml(html: string): string {
  if (!html) return html;

  return html
    .replace(
      /<span[^>]*(?:data-metadata|data-buffer)="[^"]*"[^>]*>[\s\S]*?<\/span>/g,
      '',
    )
    .replace(/<!--\s*\(figmeta\)[\s\S]*?\(\/figmeta\)\s*-->/g, '')
    .replace(/<!--\s*\(figma\)[\s\S]*?\(\/figma\)\s*-->/g, '');
}

const SideTabChrome: React.FC = () => (
  <span className={styles.sideTabShape} aria-hidden>
    <svg
      className={styles.sideTabTop}
      width="50"
      height="36"
      viewBox="0 0 50 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M49.5 0.526002C49.5 0.0639109 35.1201 5.86287 7.34502 10.4607C3.42623 11.1094 0.5 14.4713 0.5 18.4434V35.526C0.5 35.2499 0.73128 35.026 1.00742 35.026H49.0062C49.2823 35.026 49.5 35.2499 49.5 35.526V0.526002Z"
        fill="#FAFAFA"
        stroke="#FAFAFA"
      />
    </svg>
    <span className={styles.sideTabMiddleWrap}>
      <svg
        className={styles.sideTabMiddle}
        width="49"
        height="33"
        viewBox="0 0 49 33"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <rect width="49" height="33" fill="#FAFAFA" />
      </svg>
    </span>
    <svg
      className={styles.sideTabBottom}
      width="50"
      height="36"
      viewBox="0 0 50 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M49.5 35.0052C49.5 35.4673 35.1201 29.6684 7.34502 25.0705C3.42623 24.4218 0.5 21.0599 0.5 17.0878V0.00523758C0.5 0.28138 0.73128 0.505238 1.00742 0.505238H49.0062C49.2823 0.505238 49.5 0.28138 49.5 0.00523758V35.0052Z"
        fill="#FAFAFA"
        stroke="#FAFAFA"
      />
    </svg>
  </span>
);

export const CourseBuilder: React.FC<CourseBuilderProps> = ({
  courseSlug,
  lessonSlug,
  lessonHomeworks,
  onSave,
  saving,
}) => {
  const navigate = useNavigate();
  const {
    layout,
    setTitle,
    addBlockAt,
    updateBlock,
    setBlockFile,
    removeBlock,
    toJSON,
    toSubmitPayload,
  } = useLessonBuilderStore();
  const { initialize: initHomework, toJSON: homeworkToJSON } = useHomeworkStore();

  const [mounted, setMounted] = useState(false);
  const [collapsedEditors, setCollapsedEditors] = useState<
    Record<string, boolean>
  >({});
  const [activeTab, setActiveTab] = useState<'layout' | 'homework'>('layout');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deletingBlocks, setDeletingBlocks] = useState<Record<string, boolean>>({});
  const [titleCenterWidth, setTitleCenterWidth] = useState(TITLE_CENTER_MIN_WIDTH);
  const titleMeasureRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    initHomework(`${courseSlug}/${lessonSlug}`);
  }, [courseSlug, lessonSlug, initHomework]);

  useLayoutEffect(() => {
    const measureNode = titleMeasureRef.current;
    if (!measureNode) return;
    const measured = Math.ceil(measureNode.getBoundingClientRect().width) + 44;
    const nextWidth = Math.min(
      TITLE_CENTER_MAX_WIDTH,
      Math.max(TITLE_CENTER_MIN_WIDTH, measured),
    );
    setTitleCenterWidth(nextWidth);
  }, [layout.title]);

  const gridLayout = blocksToLayout(layout.blocks);
  const draggableHandleProps = {
    draggableHandle: '.block-drag-handle',
  } as const;

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

  const blockHasContent = (block: Block): boolean => {
    if (block.type === 'text') return !!block.html.replace(/<[^>]*>/g, '').trim();
    return !!block.url;
  };

  const handleDeleteBlock = (blockId: string) => {
    if (deletingBlocks[blockId]) return;
    setDeletingBlocks((prev) => ({ ...prev, [blockId]: true }));
    window.setTimeout(() => {
      removeBlock(blockId);
      setDeletingBlocks((prev) => {
        const next = { ...prev };
        delete next[blockId];
        return next;
      });
    }, 220);
  };

  const handleCourseTitleChange = (title: string) => setTitle(title);
  const handleTextChange = (blockId: string, html: string) => {
    const cleaned = sanitizeRichTextHtml(html);
    updateBlock(blockId, { html: cleaned } as Block);
  };

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
      const lessonTextFontPx =
        FONT_SIZE_STEPS[block.fontSizeIndex ?? DEFAULT_FONT_SIZE_INDEX] ??
        FONT_SIZE_STEPS[DEFAULT_FONT_SIZE_INDEX];
      return (
        <div className={`${styles.blockBody} ${styles.blockBodyText}`} dir="ltr">
          <div
            className={`${styles.richTextEditor} ${
              collapsed ? styles.richTextEditorCollapsed : ''
            }`}
          >
            <RichTextEditor
              value={block.html || ''}
              onChange={(html) => handleTextChange(block.id, html)}
              variant="compact"
              placeholder="Введите текст"
              contentFontSizePx={lessonTextFontPx}
              contentLineHeight={1.7}
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
                setBlockFile(block.id, file);
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
                setBlockFile(block.id, file);
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
      <div className={styles.builderTopBar}>
        <Link
          to={`/app/courses/${courseSlug}/${lessonSlug}`}
          className={styles.backToLesson}
          aria-label="Назад к странице урока"
        >
          <ArrowLeft size={18} strokeWidth={2} aria-hidden />
          <span>к уроку</span>
        </Link>
      </div>
      <div className={styles.lessonHeader}>
        <div className={styles.lessonHeaderTrapezoid}>
          <svg
            className={styles.lessonHeaderCapLeft}
            width="36"
            height="50"
            viewBox="0 0 36 50"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden
          >
            <path
              d="M0.526002 49.5C0.0639109 49.5 5.86287 35.1201 10.4607 7.34502C11.1094 3.42623 14.4713 0.5 18.4434 0.5H35.526C35.2499 0.5 35.026 0.73128 35.026 1.00742V49.0062C35.026 49.2823 35.2499 49.5 35.526 49.5H0.526002Z"
              fill="#FAFAFA"
              stroke="#FAFAFA"
            />
          </svg>
          <div
            className={styles.lessonHeaderCenter}
            style={{ width: `${titleCenterWidth}px` }}
          >
            <svg
              className={styles.lessonHeaderCenterSvg}
              width="82"
              height="50"
              viewBox="0 0 82 50"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              preserveAspectRatio="none"
              aria-hidden
            >
              <rect width="82" height="50" fill="#FAFAFA" />
            </svg>
            <input
              className={styles.titleInput}
              value={layout.title}
              onChange={(e) => handleCourseTitleChange(e.target.value)}
              placeholder="Название урока"
            />
            <span ref={titleMeasureRef} className={styles.titleMeasure}>
              {layout.title || 'Название урока'}
            </span>
          </div>
          <svg
            className={styles.lessonHeaderCapRight}
            width="36"
            height="50"
            viewBox="0 0 36 50"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden
          >
            <path
              d="M35.0052 49.5C35.4673 49.5 29.6684 35.1201 25.0705 7.34502C24.4218 3.42623 21.0599 0.5 17.0878 0.5H0.00523758C0.28138 0.5 0.505238 0.73128 0.505238 1.00742V49.0062C0.505238 49.2823 0.28138 49.5 0.00523758 49.5H35.0052Z"
              fill="#FAFAFA"
              stroke="#FAFAFA"
            />
          </svg>
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
            <SideTabChrome />
            <span className={styles.sideTabLabel}>конструктор</span>
          </button>
          <button
            type="button"
            className={`${styles.sideTab} ${
              activeTab === 'homework' ? styles.sideTabActive : ''
            }`}
            onClick={() => setActiveTab('homework')}
          >
            <SideTabChrome />
            <span className={styles.sideTabLabel}>домашнее задание</span>
          </button>
        </div>

        <div className={styles.mainContent}>
          {activeTab === 'layout' && (
            <div className={styles.layoutColumn}>
              <div className={styles.gridWrapper}>
                <div className={styles.gridViewport}>
                  <div
                    className={styles.gridCanvas}
                    style={{ width: GRID_FIXED_WIDTH, minWidth: GRID_FIXED_WIDTH }}
                  >
                    <GridLayout
                      className={styles.gridLayout}
                      width={GRID_FIXED_WIDTH}
                      style={{ minHeight: GRID_MIN_HEIGHT }}
                      layout={gridLayout}
                      cols={GRID_COLS}
                      rowHeight={ROW_HEIGHT}
                      margin={[GRID_GAP, GRID_GAP]}
                      measureBeforeMount={false}
                      useCSSTransforms={mounted}
                      compactType="vertical"
                      preventCollision={false}
                      onLayoutChange={onLayoutChange}
                      onDrop={onDrop}
                      isDroppable
                      {...draggableHandleProps}
                      droppingItem={{ i: '__drop__', x: 0, y: 0, w: 2, h: 2 }}
                      containerPadding={[0, 0]}
                    >
                      {layout.blocks.map((block) => (
                        <div
                          key={block.id}
                          className={`${styles.gridBlock} ${deletingBlocks[block.id] ? styles.gridBlockDeleting : ''} ${
                            block.type === 'text' && !(collapsedEditors[block.id] ?? true)
                              ? styles.gridBlockToolbarAbove
                              : ''
                          }`}
                          dir="ltr"
                        >
                          <div className={`${styles.blockHeader} block-drag-handle`}>
                            <span className={styles.blockType}>
                              {BLOCK_LABELS[block.type]}
                            </span>
                            <div className={styles.blockHeaderActions}>
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
                              <button
                                type="button"
                                className={styles.blockDeleteBtn}
                                disabled={deletingBlocks[block.id]}
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (deletingBlocks[block.id]) return;
                                  if (blockHasContent(block)) {
                                    setDeleteTarget(block.id);
                                  } else {
                                    handleDeleteBlock(block.id);
                                  }
                                }}
                                aria-label="Удалить блок"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>
                          {renderBlockBody(block)}
                        </div>
                      ))}
                    </GridLayout>
                  </div>
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
                    disabled={saving}
                    onClick={() => onSave(toSubmitPayload())}
                  >
                    {saving ? 'Сохранение…' : 'Сохранить черновик'}
                  </button>
                  <button
                    type="button"
                    className={`${styles.button} ${styles.buttonPrimary}`}
                    onClick={() => {
                      const lessonData = toJSON();
                      const homeworkData = homeworkToJSON();
                      const hw = homeworkData.questions.length > 0 ? homeworkData : null;
                      const page = serializeCoursePage(lessonData, hw);
                      navigate('/app/lesson/preview', { state: page });
                    }}
                  >
                    Предпросмотр
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'homework' && (
            <HomeworkBuilder
              courseSlug={courseSlug}
              lessonSlug={lessonSlug}
              lessonHomeworks={lessonHomeworks}
            />
          )}
        </div>
      </div>

      <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить блок?</AlertDialogTitle>
            <AlertDialogDescription>
              Блок содержит данные. Это действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeleteTarget(null)}>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (deleteTarget) handleDeleteBlock(deleteTarget);
                setDeleteTarget(null);
              }}
            >
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
