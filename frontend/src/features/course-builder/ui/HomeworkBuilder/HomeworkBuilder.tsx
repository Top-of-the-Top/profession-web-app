import React from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { GripHorizontal, GripVertical, X, Trash2 } from 'lucide-react';
import { useHomeworkStore } from '../../model/homeworkStore';
import { cn } from '../../../../shared/lib/utils';
import type {
  HomeworkQuestion,
  HomeworkQuestionType,
  HomeworkOption,
} from '../../model/homeworkTypes';
import styles from './HomeworkBuilder.module.css';

type SingleQuestion = Extract<HomeworkQuestion, { type: 'single' }>;

export const HomeworkBuilder: React.FC = () => {
  const {
    layout,
    addQuestion,
    updateQuestion,
    removeQuestion,
    reorderQuestions,
    addOption,
    updateOption,
    removeOption,
    reorderOptions,
  } = useHomeworkStore();

  const handlePaletteClick = (type: HomeworkQuestionType) => {
    addQuestion(type);
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

    // default: reorder questions
    reorderQuestions(source.index, destination.index);
  };

  return (
    <>
      <DragDropContext onDragEnd={handleDragEnd}>
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
                              <span
                                className={styles.homeworkDragHandle}
                                {...dragProvided.dragHandleProps}
                              >
                                <GripHorizontal size={14} />
                              </span>
                              <div className={styles.homeworkCardHeader}>
                                <div className={styles.homeworkCardHeaderLeft}>
                                  <input
                                    className={styles.homeworkQuestionTitle}
                                    placeholder="Вопрос без заголовка"
                                    value={question.title}
                                    onChange={(e) =>
                                      updateQuestion(question.id, {
                                        title: e.target.value,
                                      })
                                    }
                                  />
                                </div>
                              </div>
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
      </DragDropContext>
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
          >
            Сохранить черновик
          </button>
          <button
            type="button"
            className={`${styles.button} ${styles.buttonPrimary}`}
          >
            Прикрепить ДЗ
          </button>
        </div>
      </div>
    </>
  );
};
