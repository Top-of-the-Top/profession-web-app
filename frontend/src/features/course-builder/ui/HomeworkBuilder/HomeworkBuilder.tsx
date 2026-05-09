import React, { useEffect, useMemo, useState } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { GripHorizontal, GripVertical, X, Trash2, Minus, Plus } from 'lucide-react';
import { useHomeworkStore } from '../../model/homeworkStore';
import { cn } from '@shared/lib/utils';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  Button,
  Modal,
  Spinner,
} from '@shared/ui';
import {
  useCreateHomeworkWithItems,
  useDeleteHomework,
  type CreateHomeworkWithItemsPayload,
} from '@shared/api/mutations/courses';
import { useHomeworkDetail } from '@shared/api/queries/courses';
import {
  type HomeworkLayout,
  type HomeworkQuestion,
  type HomeworkQuestionType,
  type HomeworkOption,
  HOMEWORK_FILE_TASK_TEXT_PREFIX,
  validateHomeworkLayout,
  isHomeworkValid,
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
  onSaved?: () => void;
  onInitialized?: () => void;
  hasUnsavedChanges?: boolean;
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
      return { id: item.id, type: 'single', title: item.text, score: item.max_points ?? 0, options };
    }
    const taskText = item.text;
    if (taskText.startsWith(HOMEWORK_FILE_TASK_TEXT_PREFIX)) {
      return { id: item.id, type: 'file', title: '', description: taskText.slice(HOMEWORK_FILE_TASK_TEXT_PREFIX.length), score: item.max_points ?? 0 };
    }
    return { id: item.id, type: 'text', title: taskText, description: '', score: item.max_points ?? 0 };
  });
  return { lessonId, title: detail.title, deadline: toDatetimeLocalValue(detail.deadline), questions };
}

function mapLayoutToPayload(
  layout: ReturnType<typeof useHomeworkStore.getState>['layout'],
  targetType: CourseContentType,
): CreateHomeworkWithItemsPayload {
  const items: CreateHomeworkWithItemsPayload['items'] = [];
  for (const q of layout.questions) {
    if (q.type === 'single') {
      const correctOpt = q.options.find((o) => o.isCorrect);
      items.push({ kind: 'question', payload: { text: q.title, answer_options: q.options.map((o) => o.text), correct_ans: correctOpt?.text ?? null } });
    } else if (q.type === 'file') {
      const body = q.title || (q as Extract<HomeworkQuestion, { type: 'file' }>).description;
      const marked = `${HOMEWORK_FILE_TASK_TEXT_PREFIX}${body}`;
      items.push({ kind: 'task', payload: { text: marked.length > 200 ? marked.slice(0, 200) : marked, max_points: q.score } });
    } else {
      const body = q.title || (q as Extract<HomeworkQuestion, { type: 'text' }>).description;
      items.push({ kind: 'task', payload: { text: body.length > 200 ? body.slice(0, 200) : body, max_points: q.score } });
    }
  }
  return {
    homework: { title: layout.title, deadline: layout.deadline ? new Date(layout.deadline).toISOString() : '', type: targetType },
    items,
  };
}

interface QuestionTouched {
  title: boolean;
  score: boolean;
  correct: boolean;
}

export const HomeworkBuilder: React.FC<HomeworkBuilderProps> = ({
  courseSlug,
  lessonSlug,
  lessonHomeworks,
  onSaved,
  onInitialized,
  hasUnsavedChanges = false,
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
  const [initializedForSlug, setInitializedForSlug] = useState<string | null>(null);
  const [pendingSlug, setPendingSlug] = useState<string | null>(null);
  const [showSwitchDialog, setShowSwitchDialog] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const [titleTouched, setTitleTouched] = useState(false);
  const [deadlineTouched, setDeadlineTouched] = useState(false);
  const [questionTouched, setQuestionTouched] = useState<Record<string, QuestionTouched>>({});

  const errors = useMemo(() => validateHomeworkLayout(layout), [layout]);

  const createMutation = useCreateHomeworkWithItems(courseSlug, lessonSlug);
  const deleteMutation = useDeleteHomework(courseSlug, lessonSlug);
  const selectedHomeworkQuery = useHomeworkDetail(
    courseSlug,
    lessonSlug,
    selectedHomeworkSlug === 'new' ? undefined : selectedHomeworkSlug,
    { editorMode: true },
  );
  const switchItems = useMemo(
    () => lessonHomeworks.map((hw) => ({ slug: hw.homework_slug, title: hw.title || hw.homework_slug, type: hw.type })),
    [lessonHomeworks],
  );

  useEffect(() => {
    setSelectedHomeworkSlug((current) => {
      if (current !== 'new' && lessonHomeworks.some((h) => h.homework_slug === current)) return current;
      if (lessonHomeworks.length === 0) return 'new';
      return lessonHomeworks[0].homework_slug;
    });
  }, [lessonHomeworks]);

  useEffect(() => {
    setInitializedForSlug(null);
    setTitleTouched(false);
    setDeadlineTouched(false);
    setQuestionTouched({});
  }, [selectedHomeworkSlug]);

  useEffect(() => {
    if (initializedForSlug === selectedHomeworkSlug) return;
    if (selectedHomeworkSlug === 'new') {
      initHomework(`${courseSlug}/${lessonSlug}`, { lessonId: `${courseSlug}/${lessonSlug}`, title: '', deadline: '', questions: [] });
      setInitializedForSlug('new');
      setTimeout(() => onInitialized?.(), 0);
      return;
    }

    if (!selectedHomeworkQuery.data) return;
    initHomework(`${courseSlug}/${lessonSlug}`, mapHomeworkDetailToLayout(selectedHomeworkQuery.data, `${courseSlug}/${lessonSlug}`));
    setInitializedForSlug(selectedHomeworkSlug);
    setTimeout(() => onInitialized?.(), 0);
  }, [selectedHomeworkSlug, initializedForSlug, selectedHomeworkQuery.data, courseSlug, lessonSlug, initHomework]);

  const touchQuestion = (id: string, field: keyof QuestionTouched) => {
    setQuestionTouched((prev) => ({
      ...prev,
      [id]: { ...{ title: false, score: false, correct: false }, ...prev[id], [field]: true },
    }));
  };

  const touchAllAndSave = (targetType: CourseContentType) => {
    if (selectedHomeworkSlug !== 'new' && selectedHomeworkQuery.isFetching) return;
    setTitleTouched(true);
    setDeadlineTouched(true);
    const allTouched: Record<string, QuestionTouched> = {};
    for (const q of layout.questions) {
      allTouched[q.id] = { title: true, score: true, correct: true };
    }
    setQuestionTouched(allTouched);
    if (!isHomeworkValid(errors)) return;
    const payload = mapLayoutToPayload(layout, targetType);
    const isEditing = selectedHomeworkSlug !== 'new';
    createMutation.mutate(
      {
        ...payload,
        homeworkSlug: isEditing ? selectedHomeworkSlug : undefined,
        previousItems: isEditing && selectedHomeworkQuery.data
          ? selectedHomeworkQuery.data.items.map((item) => ({ id: item.id, type: item.type }))
          : [],
      },
      { onSuccess: (savedHomework) => { setSelectedHomeworkSlug(savedHomework.slug); onSaved?.(); } },
    );
  };

  const requestSwitchTo = (slug: string) => {
    if (slug === selectedHomeworkSlug) return;
    if (hasUnsavedChanges) { setPendingSlug(slug); setShowSwitchDialog(true); }
    else setSelectedHomeworkSlug(slug);
  };

  const toggleCorrectOption = (question: SingleQuestion, optionId: string) => {
    const nextOptions: HomeworkOption[] = question.options.map((opt) => ({
      ...opt,
      isCorrect: opt.id === optionId ? !opt.isCorrect : false,
    }));
    updateQuestion(question.id, { options: nextOptions } as unknown as Partial<HomeworkQuestion>);
    touchQuestion(question.id, 'correct');
  };

  const renderOptions = (question: SingleQuestion) => {
    const qErr = errors.questions[question.id];
    const qt = questionTouched[question.id];
    const options: HomeworkOption[] = question.options;

    return (
      <Droppable droppableId={`options-${question.id}`} type="option" direction="vertical">
        {(provided) => (
          <div ref={provided.innerRef} {...provided.droppableProps} className={styles.homeworkOptions}>
            {options.map((opt, index: number) => {
              const isDuplicate = qErr?.duplicateOptionIds.has(opt.id) ?? false;
              return (
                <Draggable key={opt.id} draggableId={`option-${opt.id}`} index={index}>
                  {(dragProvided) => (
                    <div
                      ref={dragProvided.innerRef}
                      {...dragProvided.draggableProps}
                      className={cn(styles.homeworkOptionRow, opt.isCorrect ? styles.homeworkOptionRowCorrect : '')}
                    >
                      <button type="button" className={styles.homeworkIconButton} {...dragProvided.dragHandleProps} aria-label="Перетащить вариант">
                        <GripVertical size={14} />
                      </button>
                      <button
                        type="button"
                        className={`${styles.homeworkOptionRadio} ${opt.isCorrect ? styles.homeworkOptionRadioActive : ''}`}
                        onClick={() => toggleCorrectOption(question, opt.id)}
                      />
                      <input
                        className={cn(styles.homeworkOptionInput, isDuplicate ? styles.fieldInvalidDuplicate : '')}
                        placeholder="Вариант ответа"
                        value={opt.text}
                        onChange={(e) => updateOption(question.id, opt.id, { text: e.target.value })}
                      />
                      {isDuplicate && (
                        <span className={styles.duplicateHint} title="Совпадает с другим вариантом">!</span>
                      )}
                      <button
                        type="button"
                        className={styles.homeworkIconButton}
                        disabled={options.length <= 2}
                        onClick={() => removeOption(question.id, opt.id)}
                        aria-label="Удалить вариант"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}
                </Draggable>
              );
            })}
            {provided.placeholder}

            <button type="button" className={styles.homeworkAddOption} onClick={() => addOption(question.id)}>
              Добавить вариант
            </button>

            {(qErr?.duplicateOptionIds.size ?? 0) > 0 && (
              <p className={styles.fieldError}>Варианты должны быть уникальными</p>
            )}
            {qt?.correct && (qErr?.noCorrect ?? false) && (
              <p className={styles.fieldError}>Отметьте верный ответ</p>
            )}
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
    if (source.droppableId === destination.droppableId && source.index === destination.index) return;
    if (type === 'option') { reorderOptions(source.droppableId.replace('options-', ''), source.index, destination.index); return; }
    reorderQuestions(source.index, destination.index);
  };

  const titleError = titleTouched && errors.title;
  const deadlineError = deadlineTouched && errors.deadline;

  return (
    <div className={styles.homeworkLayout}>
      <DragDropContext onDragEnd={handleDragEnd}>
        <div className={styles.homeworkMain}>
          <div className={styles.homeworkCanvasColumn}>
            <div className={styles.homeworkWrapper}>
              {selectedHomeworkQuery.isFetching && selectedHomeworkSlug !== 'new' && (
                <div className={styles.homeworkLoadingOverlay}><Spinner /></div>
              )}
              <Droppable droppableId="questions" type="question">
                {(provided) => (
                  <div ref={provided.innerRef} {...provided.droppableProps} className={styles.homeworkList}>
                    <div className={styles.homeworkInner}>
                      {layout.questions.map((question: HomeworkQuestion, index: number) => {
                        const qErr = errors.questions[question.id];
                        const qt = questionTouched[question.id];
                        const showTitleErr = (qt?.title ?? false) && (qErr?.title ?? false);
                        const showScoreErr = (qt?.score ?? false) && (qErr?.score ?? false);
                        return (
                          <Draggable key={question.id} draggableId={String(question.id)} index={index}>
                            {(dragProvided) => (
                              <div
                                ref={dragProvided.innerRef}
                                {...dragProvided.draggableProps}
                                className={cn(
                                  styles.homeworkCard,
                                  showTitleErr || showScoreErr ? styles.homeworkCardInvalid : '',
                                )}
                              >
                                <div className={styles.homeworkCardHeaderWrapper}>
                                  <div className={styles.homeworkCardHeader}>
                                    <div className={styles.homeworkCardHeaderLeft}>
                                      <span className={styles.homeworkQuestionTypeBadge}>{QUESTION_TYPE_LABELS[question.type]}</span>
                                      <span className={styles.homeworkDragHandle} {...dragProvided.dragHandleProps}><GripHorizontal size={14} /></span>
                                    </div>
                                  </div>
                                  <textarea
                                    className={cn(styles.homeworkQuestionTitle, showTitleErr ? styles.fieldInvalid : '')}
                                    placeholder="Вопрос без заголовка"
                                    value={question.title}
                                    rows={1}
                                    onInput={(e) => { e.currentTarget.style.height = 'auto'; e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`; }}
                                    onChange={(e) => updateQuestion(question.id, { title: e.target.value })}
                                    onBlur={() => touchQuestion(question.id, 'title')}
                                  />
                                  {showTitleErr && <p className={styles.fieldError}>Введите текст вопроса</p>}
                                </div>
                                <div className={styles.homeworkCardBody}>
                                  {question.type === 'single'
                                    ? renderOptions(question as SingleQuestion)
                                    : (
                                      <textarea
                                        className={styles.homeworkLongAnswer}
                                        placeholder="Опишите задание"
                                        value={(question as Extract<HomeworkQuestion, { type: 'text' } | { type: 'file' }>).description ?? ''}
                                        onChange={(e) => updateQuestion(question.id, { description: e.target.value } as unknown as Partial<HomeworkQuestion>)}
                                      />
                                    )}
                                </div>
                                <div className={styles.homeworkCardFooter}>
                                  <div className={cn(styles.homeworkScoreStepper, showScoreErr ? styles.stepperInvalid : '')}>
                                    <button type="button" className={styles.stepperBtn}
                                      onClick={() => { updateQuestion(question.id, { score: Math.max(0, (question.score ?? 0) - 1) }); touchQuestion(question.id, 'score'); }}
                                    ><Minus size={12} /></button>
                                    <input
                                      type="number"
                                      min={0}
                                      className={styles.homeworkScoreInput}
                                      value={question.score > 0 ? question.score : ''}
                                      placeholder="0"
                                      onChange={(e) => {
                                        const numeric = e.target.value === '' ? 0 : Number(e.target.value);
                                        if (!Number.isNaN(numeric)) updateQuestion(question.id, { score: numeric });
                                      }}
                                      onBlur={() => touchQuestion(question.id, 'score')}
                                    />
                                    <button type="button" className={styles.stepperBtn}
                                      onClick={() => { updateQuestion(question.id, { score: (question.score ?? 0) + 1 }); touchQuestion(question.id, 'score'); }}
                                    ><Plus size={12} /></button>
                                    <span className={styles.homeworkScoreLabel}>баллов</span>
                                  </div>
                                  {showScoreErr && <span className={styles.scoreError}>укажите баллы</span>}
                                  <button type="button" className={cn(styles.homeworkIconButton, styles.deleteButton)} onClick={() => removeQuestion(question.id)}>
                                    <Trash2 size={16} />
                                  </button>
                                </div>
                              </div>
                            )}
                          </Draggable>
                        );
                      })}
                      {provided.placeholder}
                    </div>
                  </div>
                )}
              </Droppable>
            </div>
            <div className={styles.homeworkActionsBar}>
              <div className={styles.homeworkAddButtons}>
                <button type="button" className={styles.homeworkAddQuestionButton} onClick={() => addQuestion('single')}>+ Варианты ответов</button>
                <button type="button" className={styles.homeworkAddQuestionButton} onClick={() => addQuestion('text')}>+ Развернутый ответ</button>
                <button type="button" className={styles.homeworkAddQuestionButton} onClick={() => addQuestion('file')}>+ Файл</button>
              </div>
              <div className={styles.homeworkCtaButtons}>
                <span className={hasUnsavedChanges ? styles.unsavedIndicatorDirty : styles.unsavedIndicatorSaved}>
                  {createMutation.isPending ? 'Сохранение...' : hasUnsavedChanges ? 'Не сохранено' : 'Сохранено'}
                </span>
                <button
                  type="button"
                  className={`${styles.button} ${styles.buttonPrimary}`}
                  disabled={createMutation.isPending || selectedHomeworkQuery.isFetching}
                  onClick={() => touchAllAndSave('published')}
                >
                  Прикрепить ДЗ
                </button>
              </div>
            </div>
          </div>

          <aside className={styles.homeworkSidebar}>
            <div className={styles.homeworkSidebarSection}>
              <p className={styles.homeworkSidebarSectionLabel}>{selectedHomeworkSlug === 'new' ? 'Новое ДЗ' : 'Редактирование'}</p>

              <div className={cn(styles.tooltipWrap, titleError ? styles.tooltipWrapError : '')}>
                <input
                  className={cn(styles.homeworkTitleInput, titleError ? styles.fieldInvalidUnderline : '')}
                  placeholder="Название домашнего задания"
                  value={layout.title}
                  onChange={(e) => setTitle(e.target.value)}
                  onBlur={() => setTitleTouched(true)}
                />
                {titleError && <span className={styles.tooltip}>Введите название</span>}
              </div>

              <div className={cn(styles.tooltipWrap, deadlineError ? styles.tooltipWrapError : '')}>
                <input
                  type="datetime-local"
                  className={cn(styles.homeworkDeadlineInput, deadlineError ? styles.fieldInvalidUnderline : '')}
                  value={layout.deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                  onBlur={() => setDeadlineTouched(true)}
                />
                {deadlineError && <span className={styles.tooltip}>Укажите дедлайн</span>}
              </div>
            </div>

            <div className={styles.homeworkSidebarDivider} />

            <p className={styles.homeworkSidebarSectionLabel}>Прикреплённые ДЗ</p>
            <div className={styles.homeworkSwitchList}>
              {selectedHomeworkSlug === 'new' && (
                <div className={`${styles.homeworkSwitchButton} ${styles.homeworkSwitchButtonActive}`}>
                  <div className={styles.homeworkSwitchBody}>
                    <span className={styles.homeworkSwitchTitle}>Новое ДЗ</span>
                    <span className={`${styles.homeworkSwitchType} ${styles.homeworkSwitchTypeDraft}`}>черновик</span>
                  </div>
                </div>
              )}
              {switchItems.map((item) => (
                <div key={item.slug} className={`${styles.homeworkSwitchButton} ${selectedHomeworkSlug === item.slug ? styles.homeworkSwitchButtonActive : ''}`}>
                  <button type="button" className={styles.homeworkSwitchButtonMain} onClick={() => requestSwitchTo(item.slug)} disabled={createMutation.isPending}>
                    <span className={styles.homeworkSwitchTitle}>{item.title}</span>
                    <span className={`${styles.homeworkSwitchType} ${item.type === 'published' ? styles.homeworkSwitchTypePublished : styles.homeworkSwitchTypeDraft}`}>
                      {item.type === 'published' ? 'опубл.' : 'черновик'}
                    </span>
                  </button>
                  <button type="button" className={styles.homeworkSwitchDeleteBtn} onClick={(e) => { e.stopPropagation(); setDeleteTarget(item.slug); }} disabled={deleteMutation.isPending} title="Удалить">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {switchItems.length === 0 && selectedHomeworkSlug !== 'new' && (
                <p className={styles.homeworkSidebarEmpty}>Нет прикреплённых ДЗ</p>
              )}
            </div>

            <button type="button" className={styles.homeworkSidebarAddBtn} disabled={createMutation.isPending} onClick={() => requestSwitchTo('new')}>
              + Новое ДЗ
            </button>
          </aside>

          <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Удалить домашнее задание?</AlertDialogTitle>
                <AlertDialogDescription>Это действие необратимо. Все вопросы и попытки студентов будут удалены.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel onClick={() => setDeleteTarget(null)}>Отмена</AlertDialogCancel>
                <AlertDialogAction className={styles.deleteActionBtn} onClick={() => { if (!deleteTarget) return; const slug = deleteTarget; setDeleteTarget(null); if (selectedHomeworkSlug === slug) setSelectedHomeworkSlug('new'); deleteMutation.mutate(slug); }}>
                  Удалить
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <Modal open={showSwitchDialog} onClose={() => { setShowSwitchDialog(false); setPendingSlug(null); }} panelClassName={styles.switchDialog}>
            <p className={styles.switchDialogText}>Есть несохранённые изменения. Перейти без сохранения?</p>
            <div className={styles.switchDialogActions}>
              <Button type="button" variant="outline" onClick={() => { setShowSwitchDialog(false); setPendingSlug(null); }}>Остаться</Button>
              <Button type="button" className={styles.homeworkDialogPrimaryBtn} onClick={() => { setShowSwitchDialog(false); if (pendingSlug !== null) setSelectedHomeworkSlug(pendingSlug); setPendingSlug(null); }}>Перейти</Button>
            </div>
          </Modal>
        </div>
      </DragDropContext>
    </div>
  );
};
