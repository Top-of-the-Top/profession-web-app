import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable';
import React, { useEffect, useMemo, useState } from 'react';
import { courseBuilderApi } from '../../api/courseBuilderApi';
import { useCourseBuilderStore } from '../../model/store';
import type { Block, BlockType, Lesson, Module } from '../../model/types';
import styles from './CourseBuilder.module.css';

interface CourseBuilderProps {
  courseId: number;
}

const BLOCK_LABELS: Record<BlockType, string> = {
  text: 'Текст',
  video: 'Видео',
  homework: 'Домашнее задание',
  quiz: 'Тестовый вопрос',
};

const useDebouncedCallback = (callback: () => void, delay: number) => {
  const [timeoutId, setTimeoutId] = useState<number | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [timeoutId]);

  const schedule = () => {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
    const id = window.setTimeout(() => {
      callback();
    }, delay);
    setTimeoutId(id);
  };

  return schedule;
};

export const CourseBuilder: React.FC<CourseBuilderProps> = ({ courseId }) => {
  const {
    structure,
    selectedModuleId,
    selectedLessonId,
    isSaving,
    initialize,
    selectLesson,
    addModule,
    addLesson,
    addBlock,
    updateBlock,
    reorderBlocks,
    toJSON,
    startSaving,
    finishSaving,
  } = useCourseBuilderStore();

  const selectedModule: Module | undefined = useMemo(
    () => structure.modules.find((m) => m.id === selectedModuleId),
    [structure.modules, selectedModuleId],
  );

  const selectedLesson: Lesson | undefined = useMemo(
    () => selectedModule?.lessons.find((l) => l.id === selectedLessonId),
    [selectedModule, selectedLessonId],
  );

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const scheduleSave = useDebouncedCallback(async () => {
    startSaving();
    try {
      const payload = toJSON();
      await courseBuilderApi.save({ courseId, structure: payload });
    } finally {
      finishSaving();
    }
  }, 800);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await courseBuilderApi.load(courseId);
        initialize(data);
      } catch {
        // оставляем структуру по умолчанию
      }
    };
    void load();
  }, [courseId, initialize]);

  useEffect(() => {
    if (structure.modules.length === 0) return;
    scheduleSave();
  }, [structure, scheduleSave]);

  const handleAddBlock = (type: BlockType) => {
    if (!selectedLesson) return;
    addBlock(selectedLesson.id, type);
  };

  const handleBlockChange = (blockId: string, patch: Partial<Block>) => {
    if (!selectedLesson) return;
    updateBlock(selectedLesson.id, blockId, patch);
  };

  const handleDragEnd = (event: any) => {
    const { active, over } = event;
    if (!selectedLesson || !over || active.id === over.id) return;

    const oldIndex = selectedLesson.blocks.findIndex((b) => b.id === active.id);
    const newIndex = selectedLesson.blocks.findIndex((b) => b.id === over.id);

    if (oldIndex === -1 || newIndex === -1) return;

    reorderBlocks(selectedLesson.id, oldIndex, newIndex);
  };

  const handleCourseTitleChange = (title: string) => {
    // пока простое обновление заголовка курса
    // чтобы не раздувать стор, обновим через initialize
    initialize({ ...structure, title });
  };

  const renderBlockFields = (block: Block) => {
    switch (block.type) {
      case 'text':
        return (
          <textarea
            className={styles.textarea}
            placeholder="Текст урока..."
            value={block.content ?? ''}
            onChange={(e) => handleBlockChange(block.id, { content: e.target.value } as Block)}
          />
        );
      case 'video':
        return (
          <div className={styles.blockBody}>
            <input
              className={styles.input}
              placeholder="Ссылка на видео"
              value={block.url ?? ''}
              onChange={(e) => handleBlockChange(block.id, { url: e.target.value } as Block)}
            />
            <textarea
              className={styles.textarea}
              placeholder="Описание видео (опционально)"
              value={block.description ?? ''}
              onChange={(e) =>
                handleBlockChange(block.id, { description: e.target.value } as Block)
              }
            />
          </div>
        );
      case 'homework':
        return (
          <div className={styles.blockBody}>
            <textarea
              className={styles.textarea}
              placeholder="Задание для студентов..."
              value={block.instructions ?? ''}
              onChange={(e) =>
                handleBlockChange(block.id, { instructions: e.target.value } as Block)
              }
            />
          </div>
        );
      case 'quiz':
        return (
          <div className={styles.blockBody}>
            <input
              className={styles.input}
              placeholder="Вопрос"
              value={block.question ?? ''}
              onChange={(e) => handleBlockChange(block.id, { question: e.target.value } as Block)}
            />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className={styles.courseBuilder}>
      <div className={styles.sidebar}>
        <div className={styles.modulesHeader}>
          <span>Структура курса</span>
          <button type="button" className={styles.button} onClick={addModule}>
            + Модуль
          </button>
        </div>
        <div className={styles.modulesList}>
          {structure.modules.map((module) => (
            <div
              key={module.id}
              className={`${styles.moduleItem} ${
                module.id === selectedModuleId ? styles.moduleItemActive : ''
              }`}
            >
              <div className={styles.moduleTitleRow}>
                <span className={styles.moduleTitle}>{module.title}</span>
                <button
                  type="button"
                  className={styles.button}
                  onClick={() => addLesson(module.id)}
                >
                  + Урок
                </button>
              </div>
              <div className={styles.lessonsList}>
                {module.lessons.map((lesson) => (
                  <button
                    key={lesson.id}
                    type="button"
                    className={`${styles.lessonItem} ${
                      lesson.id === selectedLessonId ? styles.lessonItemActive : ''
                    }`}
                    onClick={() => selectLesson(module.id, lesson.id)}
                  >
                    {lesson.title}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.content}>
        <div className={styles.header}>
          <input
            className={styles.titleInput}
            value={structure.title}
            onChange={(e) => handleCourseTitleChange(e.target.value)}
          />
          <div className={styles.toolbar}>
            <span
              className={`${styles.statusDot} ${
                isSaving ? styles.saving : ''
              }`}
            />
            <span>{isSaving ? 'Сохранение...' : 'Все изменения сохранены'}</span>
          </div>
        </div>

        <div className={styles.palette}>
          {(Object.keys(BLOCK_LABELS) as BlockType[]).map((type) => (
            <button
              key={type}
              type="button"
              className={styles.paletteButton}
              onClick={() => handleAddBlock(type)}
            >
              {BLOCK_LABELS[type]}
            </button>
          ))}
        </div>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={selectedLesson?.blocks.map((b) => b.id) ?? []}>
            <div className={styles.blocksContainer}>
              {selectedLesson ? (
                selectedLesson.blocks.length === 0 ? (
                  <span className={styles.emptyState}>
                    Добавьте первый блок, чтобы начать собирать урок.
                  </span>
                ) : (
                  selectedLesson.blocks.map((block) => (
                    <div key={block.id} className={styles.blockCard}>
                      <div className={styles.blockHeader}>
                        <span className={styles.blockType}>
                          {BLOCK_LABELS[block.type]}
                        </span>
                        <span className={styles.badge}>Блок</span>
                      </div>
                      {renderBlockFields(block)}
                    </div>
                  ))
                )
              ) : (
                <span className={styles.emptyState}>
                  Создайте модуль и урок, чтобы начать.
                </span>
              )}
            </div>
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
};

