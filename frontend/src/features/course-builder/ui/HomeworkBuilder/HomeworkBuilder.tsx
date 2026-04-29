import React, { useEffect, useMemo, useState } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { GripHorizontal, GripVertical, X, Trash2 } from 'lucide-react';
import { useHomeworkStore } from '../../model/homeworkStore';
import { cn } from '@shared/lib/utils';
import { notifyWarning } from '@shared/lib/sileo/notify';
import {
  useCreateHomeworkWithItems,
  type CreateHomeworkWithItemsPayload,
} from '@shared/api/mutations/courses';
import { useHomeworkDetail } from '@shared/api/queries/courses';
import type {
  HomeworkLayout,
  HomeworkQuestion,
  HomeworkQuestionType,
  HomeworkOption,
} from '../../model/homeworkTypes';
import type {
  CourseContentType,
  HomeworkDetail,
  LessonHomework,
} from '@shared/api/courseApi';
import styles from './HomeworkBuilder.module.css';

type SingleQuestion = Extract<HomeworkQuestion, { type: 'single' }>;

const QUESTION_TYPE_LABELS: Record<HomeworkQuestionType, string> = {
  single: 'Варианты ответов',
  text: 'Развернутый ответ',
  file: 'Файл',
};

interface HomeworkBuilderProps {
  courseSlug: string;
  lessonSlug: string;
  lessonHomeworks: LessonHomework[];
}

function toDatetimeLocalValue(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function mapHomeworkDetailToLayout(
  detail: HomeworkDetail,
  lessonId: string,
): HomeworkLayout {
  const questions: HomeworkQuestion[] = detail.items.map((item) => {
    if (item.type === 'question') {
      const options = (item.answer_options ?? []).map((text, idx) => ({
        id: `${item.id}-opt-${idx}`,
        text,
        isCorrect: item.correct_ans === text,
      }));
      return {
        id: item.id,
        type: 'single',
        title: item.text,
        score: item.max_points ?? 0,
        options,
      };
    }
    return {
      id: item.id,
      type: 'text',
      title: item.text,
      description: '',
      score: item.max_points ?? 0,
    };
  });

  return {
    lessonId,
    title: detail.title,
    deadline: toDatetimeLocalValue(detail.deadline),
    questions,
  };
}

function mapLayoutToPayload(
  layout: ReturnType<typeof useHomeworkStore.getState>['layout'],
  targetType: CourseContentType,
): CreateHomeworkWithItemsPayload {
  const items: CreateHomeworkWithItemsPayload['items'] = [];

  for (const q of layout.questions) {
    if (q.type === 'single') {
      const correctOpt = q.options.find((o) => o.isCorrect);
      items.push({
        kind: 'question',
        payload: {
          text: q.title,
          answer_options: q.options.map((o) => o.text),
          correct_ans: correctOpt?.text ?? null,
        },
      });
    } else {
      items.push({
        kind: 'task',
        payload: {
          text: q.title || (q as Extract<HomeworkQuestion, { type: 'text' } | { type: 'file' }>).description,
          max_points: q.score,
        },
      });
    }
  }

  return {
    homework: {
      title: layout.title,
      deadline: new Date(layout.deadline).toISOString(),
      type: targetType,
    },
    items,
  };
}

export const HomeworkBuilder: React.FC<HomeworkBuilderProps> = ({
  courseSlug,
  lessonSlug,
  lessonHomeworks,
}) => {
  const {
    layout,
    initialize: initHomework,
    setTitle,
    setDeadline,
    addQuestion,
    updateQuestion,
    removeQuestion,
    reorderQuestions,
    addOption,
    updateOption,
    removeOption,
    reorderOptions,
  } = useHomeworkStore();

  const [selectedHomeworkSlug, setSelectedHomeworkSlug] = useState<string>('new');
  const createMutation = useCreateHomeworkWithItems(courseSlug, lessonSlug);
  const selectedHomeworkQuery = useHomeworkDetail(
    courseSlug,
    lessonSlug,
    selectedHomeworkSlug === 'new' ? undefined : selectedHomeworkSlug,
  );
  const switchItems = useMemo(
    () => [
      { slug: 'new', title: 'Новое ДЗ', type: 'draft' as CourseContentType },
      ...lessonHomeworks.map((hw) => ({
        slug: hw.homework_slug,
        title: hw.title || hw.homework_slug,
        type: hw.type,
      })),
    ],
    [lessonHomeworks],
  );

  useEffect(() => {
    setSelectedHomeworkSlug((current) => {
      if (current !== 'new' && lessonHomeworks.some((h) => h.homework_slug === current)) {
        return current;
      }
      if (lessonHomeworks.length === 0) return 'new';
      return lessonHomeworks[0].homework_slug;
    });
  }, [lessonHomeworks]);

  useEffect(() => {
    if (selectedHomeworkSlug === 'new') {
      initHomework(`${courseSlug}/${lessonSlug}`, {
        lessonId: `${courseSlug}/${lessonSlug}`,
        title: '',
        deadline: '',
        questions: [],
      });
      return;
    }
    if (!selectedHomeworkQuery.data) return;
    initHomework(
      `${courseSlug}/${lessonSlug}`,
      mapHomeworkDetailToLayout(
        selectedHomeworkQuery.data,
        `${courseSlug}/${lessonSlug}`,
      ),
    );
  }, [
    selectedHomeworkSlug,
    selectedHomeworkQuery.data,
    courseSlug,
    lessonSlug,
    initHomework,
  ]);

  const handlePaletteClick = (type: HomeworkQuestionType) => {
    addQuestion(type);
  };

  const validate = (): boolean => {
    if (!layout.title.trim()) {
      notifyWarning({ title: 'Укажите название задания' });
      return false;
    }
    if (!layout.deadline) {
      notifyWarning({ title: 'Укажите дедлайн' });
      return false;
    }
    if (layout.questions.length === 0) {
      notifyWarning({ title: 'Добавьте хотя бы один вопрос' });
      return false;
    }
    return true;
  };

  const handleSave = (targetType: CourseContentType) => {
    if (selectedHomeworkSlug !== 'new' && selectedHomeworkQuery.isFetching) return;
    if (!validate()) return;
    const payload = mapLayoutToPayload(layout, targetType);
    const isEditing = selectedHomeworkSlug !== 'new';
    createMutation.mutate(
      {
        ...payload,
        homeworkSlug: isEditing ? selectedHomeworkSlug : undefined,
        previousItems:
          isEditing && selectedHomeworkQuery.data
            ? selectedHomeworkQuery.data.items.map((item) => ({
                id: item.id,
                type: item.type,
              }))
            : [],
      },
      {
        onSuccess: (savedHomework) => {
          setSelectedHomeworkSlug(savedHomework.slug);
        },
      },
    );
  };

  const toggleCorrectOption = (question: SingleQuestion, optionId: string) => {
    const nextOptions: HomeworkOption[] = question.options.map((opt) => {
      if (opt.id !== optionId) {
        return { ...opt, isCorrect: false };
      }
      const nextValue = !opt.isCorrect;
      return { ...opt, isCorrect: nextValue };
    });

    updateQuestion(question.id, {
      options: nextOptions,
    } as unknown as Partial<HomeworkQuestion>);
  };

  const renderOptions = (question: SingleQuestion) => {
    const options: HomeworkOption[] = question.options;

    return (
      <Droppable
        droppableId={`options-${question.id}`}
        type="option"
        direction="vertical"
      >
        {(provided) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={styles.homeworkOptions}
          >
            {options.map((opt, index: number) => (
              <Draggable
                key={opt.id}
                draggableId={`option-${opt.id}`}
                index={index}
              >
                {(dragProvided) => (
                  <div
                    ref={dragProvided.innerRef}
                    {...dragProvided.draggableProps}
                    className={cn(
                      styles.homeworkOptionRow,
                      opt.isCorrect ? styles.homeworkOptionRowCorrect : ''
                    )}
                  >
                    <button
                      type="button"
                      className={styles.homeworkIconButton}
                      {...dragProvided.dragHandleProps}
                      aria-label="Перетащить вариант"
                    >
                      <GripVertical size={14} />
                    </button>
                    <button
                      type="button"
                      className={`${styles.homeworkOptionRadio} ${
                        opt.isCorrect ? styles.homeworkOptionRadioActive : ''
                      }`}
                      onClick={() => toggleCorrectOption(question, opt.id)}
                    />
                    <input
                      className={styles.homeworkOptionInput}
                      placeholder="Вариант ответа"
                      value={opt.text}
                      onChange={(e) =>
                        updateOption(question.id, opt.id, {
                          text: e.target.value,
                        })
                      }
                    />

                    <button
                      type="button"
                      className={styles.homeworkIconButton}
                      onClick={() => removeOption(question.id, opt.id)}
                      aria-label="Удалить вариант"
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
              </Draggable>
            ))}
            {provided.placeholder}

            <button
              type="button"
              className={styles.homeworkAddOption}
              onClick={() => addOption(question.id)}
            >
              Добавить вариант
            </button>
          </div>
        )}
      </Droppable>
    );
  };

  const handleDragEnd = (result: {
    source?: { droppableId: string; index: number };
    destination?: { droppableId: string; index: number } | null;
    type: string;
  }) => {
    const { source, destination, type } = result;
    if (!source || !destination) return;
    if (
      source.droppableId === destination.droppableId &&
      source.index === destination.index
    ) {
      return;
    }

    if (type === 'option') {
      const questionId = source.droppableId.replace('options-', '');
      reorderOptions(questionId, source.index, destination.index);
      return;
    }

    reorderQuestions(source.index, destination.index);
  };

  return (
    <div className={styles.homeworkLayout}>
      {selectedHomeworkQuery.isFetching && selectedHomeworkSlug !== 'new' && (
        <div className={styles.homeworkLoadingHint}>Загрузка выбранного ДЗ...</div>
      )}
      <DragDropContext onDragEnd={handleDragEnd}>
        <div className={styles.homeworkMain}>
          <div className={styles.homeworkCanvasColumn}>
            <div className={styles.homeworkWrapper}>
              <Droppable droppableId="questions" type="question">
                {(provided) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={styles.homeworkList}
                  >
                    <div className={styles.homeworkInner}>
                      {layout.questions.map(
                        (question: HomeworkQuestion, index: number) => (
                          <Draggable
                            key={question.id}
                            draggableId={String(question.id)}
                            index={index}
                          >
                            {(dragProvided) => (
                              <div
                                ref={dragProvided.innerRef}
                                {...dragProvided.draggableProps}
                                className={styles.homeworkCard}
                              >
                                <div className={styles.homeworkCardHeaderWrapper}>
                                  <div className={styles.homeworkCardHeader}>
                                    <div className={styles.homeworkCardHeaderLeft}>
                                      <span className={styles.homeworkQuestionTypeBadge}>
                                        {QUESTION_TYPE_LABELS[question.type]}
                                      </span>
                                      <span
                                        className={styles.homeworkDragHandle}
                                        {...dragProvided.dragHandleProps}
                                      >
                                        <GripHorizontal size={14} />
                                      </span>
                                    </div>
                                  </div>
                                  <textarea
                                    className={styles.homeworkQuestionTitle}
                                    placeholder="Вопрос без заголовка"
                                    value={question.title}
                                    rows={1}
                                    onInput={(e) => {
                                      e.currentTarget.style.height = 'auto';
                                      e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`;
                                    }}
                                    onChange={(e) =>
                                      updateQuestion(question.id, {
                                        title: e.target.value,
                                      })
                                    }
                                  />
                                </div>
                                <div className={styles.homeworkCardBody}>
                                  {question.type === 'single' ? (
                                    renderOptions(question as SingleQuestion)
                                  ) : (
                                    <textarea
                                      className={styles.homeworkLongAnswer}
                                      placeholder="Опишите задание"
                                      value={
                                        (
                                          question as Extract<
                                            HomeworkQuestion,
                                            { type: 'text' } | { type: 'file' }
                                          >
                                        ).description ?? ''
                                      }
                                      onChange={(e) =>
                                        updateQuestion(question.id, {
                                          description: e.target.value,
                                        } as unknown as Partial<HomeworkQuestion>)
                                      }
                                    />
                                  )}
                                </div>

                                <div className={styles.homeworkCardFooter}>
                                  <span className={styles.homeworkScoreLabel}>
                                    Баллы
                                  </span>
                                  <input
                                    type="number"
                                    min={0}
                                    className={styles.homeworkScoreInput}
                                    value={
                                      Number.isFinite(question.score) &&
                                      question.score !== 0
                                        ? question.score
                                        : ''
                                    }
                                    onChange={(e) => {
                                      const { value } = e.target;
                                      if (value === '') {
                                        updateQuestion(question.id, {
                                          score: 0,
                                        });
                                        return;
                                      }
                                      const numeric = Number(value);
                                      if (Number.isNaN(numeric)) return;
                                      updateQuestion(question.id, {
                                        score: numeric,
                                      });
                                    }}
                                  />
                                  <button
                                    type="button"
                                    className={styles.homeworkIconButton}
                                    onClick={() => removeQuestion(question.id)}
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                </div>
                              </div>
                            )}
                          </Draggable>
                        )
                      )}
                      {provided.placeholder}
                    </div>
                  </div>
                )}
              </Droppable>
            </div>
            <div className={styles.homeworkActionsBar}>
              <div className={styles.homeworkAddButtons}>
                <button
                  type="button"
                  className={styles.homeworkAddQuestionButton}
                  onClick={() => handlePaletteClick('single')}
                >
                  + Варианты ответов
                </button>
                <button
                  type="button"
                  className={styles.homeworkAddQuestionButton}
                  onClick={() => handlePaletteClick('text')}
                >
                  + Развернутый ответ
                </button>
                <button
                  type="button"
                  className={styles.homeworkAddQuestionButton}
                  onClick={() => handlePaletteClick('file')}
                >
                  + Файл
                </button>
                </div>
              <div className={styles.homeworkCtaButtons}>
                <button
                  type="button"
                  className={`${styles.button} ${styles.buttonSecondary}`}
                  disabled={createMutation.isPending || selectedHomeworkQuery.isFetching}
                  onClick={() => handleSave('draft')}
                >
                  Сохранить черновик
                </button>
                <button
                  type="button"
                  className={`${styles.button} ${styles.buttonPrimary}`}
                  disabled={createMutation.isPending || selectedHomeworkQuery.isFetching}
                  onClick={() => handleSave('published')}
                >
                  Прикрепить ДЗ
                </button>
              </div>
            </div>
          </div>
          <aside className={styles.homeworkSidebar}>
            <div className={styles.homeworkSidebarTitle}>Домашние задания</div>
            <div className={styles.homeworkHeader}>
              <input
                className={styles.homeworkTitleInput}
                placeholder="Название домашнего задания"
                value={layout.title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <input
                type="datetime-local"
                className={styles.homeworkDeadlineInput}
                value={layout.deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </div>
            <div className={styles.homeworkSwitchList}>
              {switchItems.map((item) => (
                <button
                  key={item.slug}
                  type="button"
                  className={`${styles.homeworkSwitchButton} ${
                    selectedHomeworkSlug === item.slug
                      ? styles.homeworkSwitchButtonActive
                      : ''
                  }`}
                  onClick={() => setSelectedHomeworkSlug(item.slug)}
                  disabled={createMutation.isPending}
                >
                  <span className={styles.homeworkSwitchTitle}>{item.title}</span>
                  <span
                    className={`${styles.homeworkSwitchType} ${
                      item.type === 'published'
                        ? styles.homeworkSwitchTypePublished
                        : styles.homeworkSwitchTypeDraft
                    }`}
                  >
                    {item.type === 'published' ? 'опубликовано' : 'черновик'}
                  </span>
                </button>
              ))}
            </div>
          </aside>
        </div>
      </DragDropContext>
    </div>
  );
};
