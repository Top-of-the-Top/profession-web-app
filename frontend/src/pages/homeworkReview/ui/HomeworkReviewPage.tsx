import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
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
  PageFrame,
  RichTextEditor,
  SafeHtml,
  Spinner,
} from '@shared/ui';
import { getHomeworkReviewBackHref } from '@shared/lib/homeworkReviewNavigation';
import { useReviewHomeworkAttempt } from '@shared/api/mutations/courses';
import { useHomeworkAttemptForReview, useHomeworkDetail } from '@shared/api/queries/courses';
import { HOMEWORK_FILE_TASK_TEXT_PREFIX } from '../../../features/course-builder/model/homeworkTypes';
import type { HomeworkAttemptTaskItem, ReviewHomeworkAttemptItemPayload } from '@shared/api/courseApi';
import { notifySuccess } from '@shared/lib/sileo/notify';
import { useReviewDraft, readReviewDraft, clearReviewDraft } from '../lib/useReviewDraft';
import styles from './HomeworkReviewPage.module.css';

type ReviewDraft = {
  points: number;
  comment: string;
};

function pointsLabel(value: number): string {
  const mod10 = value % 10;
  const mod100 = value % 100;
  if (mod10 === 1 && mod100 !== 11) return `${value} балл`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${value} балла`;
  return `${value} баллов`;
}

function isFileTask(item: HomeworkAttemptTaskItem): boolean {
  return item.text.startsWith(HOMEWORK_FILE_TASK_TEXT_PREFIX);
}

function taskPrompt(item: HomeworkAttemptTaskItem): string {
  if (!isFileTask(item)) return item.text;
  return item.text.slice(HOMEWORK_FILE_TASK_TEXT_PREFIX.length).trim();
}

export default function HomeworkReviewPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { slug: courseSlug, lessonSlug, homeworkSlug, attemptId } = useParams<{
    slug: string;
    lessonSlug: string;
    homeworkSlug: string;
    attemptId: string;
  }>();

  const attemptQuery = useHomeworkAttemptForReview(courseSlug, attemptId);
  const homeworkQuery = useHomeworkDetail(courseSlug, lessonSlug, homeworkSlug);
  const reviewMutation = useReviewHomeworkAttempt(courseSlug ?? '', attemptId ?? '');

  const { persist: persistDraft } = useReviewDraft(attemptId);

  const items = attemptQuery.data?.items ?? [];
  const [step, setStep] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, ReviewDraft>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    if (!attemptQuery.data) return;
    const isAlreadyReviewed = attemptQuery.data.status === 'reviewed';
    const saved = !isAlreadyReviewed && attemptId ? readReviewDraft(attemptId) : null;

    const nextDrafts: Record<string, ReviewDraft> = {};
    for (const item of attemptQuery.data.items) {
      if (item.type !== 'task') continue;
      // If reviewed — use server data; if draft in LS exists — prefer it; else default
      if (isAlreadyReviewed) {
        nextDrafts[item.answer_id] = {
          points: item.review?.points ?? 0,
          comment: item.review?.comment ?? '',
        };
      } else {
        const ls = saved?.drafts[item.answer_id];
        nextDrafts[item.answer_id] = {
          points: ls?.points ?? item.review?.points ?? 0,
          comment: ls?.comment ?? item.review?.comment ?? '',
        };
      }
    }
    setDrafts(nextDrafts);
  }, [attemptQuery.data, attemptId]);

  const currentItem = items[step];
  const isReviewed = attemptQuery.data?.status === 'reviewed';

  // Persist draft to localStorage on every change (skip when already reviewed)
  useEffect(() => {
    if (isReviewed || Object.keys(drafts).length === 0) return;
    persistDraft(drafts);
  }, [drafts, isReviewed, persistDraft]);

  type StepBubbleState = 'correct' | 'wrong' | 'filled' | 'empty';

  function stepBubbleState(item: (typeof items)[number]): StepBubbleState {
    if (item.type === 'question') {
      return item.status === 'correct' ? 'correct' : 'wrong';
    }
    if (isReviewed) {
      const points = item.review?.points ?? 0;
      return points > 0 ? 'correct' : 'wrong';
    }
    const d = drafts[item.answer_id];
    if (d && (d.points > 0 || d.comment.trim())) return 'filled';
    return 'empty';
  }

  const reviewItems = useMemo(() => {
    const onlyTasks = items.filter((item): item is HomeworkAttemptTaskItem => item.type === 'task');
    return onlyTasks.map((item) => {
      const draft = drafts[item.answer_id];
      return {
        task_answer_id: item.answer_id,
        points: draft?.points ?? 0,
        comment: draft?.comment?.trim() ? draft.comment : null,
      } satisfies ReviewHomeworkAttemptItemPayload;
    });
  }, [drafts, items]);

  if (!courseSlug || !lessonSlug || !homeworkSlug || !attemptId) {
    return (
      <PageFrame>
        <div className={styles.centered}>Некорректный адрес.</div>
      </PageFrame>
    );
  }

  if (attemptQuery.isLoading || homeworkQuery.isLoading) {
    return (
      <PageFrame>
        <div className={styles.centered}><Spinner /></div>
      </PageFrame>
    );
  }

  if (attemptQuery.isError || !attemptQuery.data || homeworkQuery.isError || !homeworkQuery.data) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <Button type="button" onClick={() => { void attemptQuery.refetch(); void homeworkQuery.refetch(); }}>
            Обновить
          </Button>
        </div>
      </PageFrame>
    );
  }

  if (!currentItem) {
    return (
      <PageFrame>
        <div className={styles.centered}>Нет данных для проверки.</div>
      </PageFrame>
    );
  }

  const backHref = getHomeworkReviewBackHref(location.state, courseSlug, lessonSlug);
  const attemptsListPath = `/app/courses/${courseSlug}/${lessonSlug}/homework/${homeworkSlug}/review`;

  return (
    <PageFrame>
      <div className={styles.pageRoot}>
        <div className={styles.centeredColumn}>
          <div className={styles.backNavWrap}>
            <Link to={backHref} className={styles.backNav}>
              <ChevronLeft size={18} strokeWidth={2} aria-hidden />
              Назад
            </Link>
          </div>

          <div className={styles.steps}>
            {items.map((item, idx) => {
              const bubbleState = stepBubbleState(item);
              const cls = [
                styles.step,
                bubbleState === 'empty' ? styles.stepEmpty : '',
                bubbleState === 'filled' ? styles.stepFilled : '',
                bubbleState === 'correct' ? styles.stepCorrect : '',
                bubbleState === 'wrong' ? styles.stepWrong : '',
                idx === step ? styles.stepActive : '',
              ].join(' ');
              return (
                <button
                  key={item.type === 'task' ? item.task_id : item.question_id}
                  type="button"
                  className={cls}
                  onClick={() => setStep(idx)}
                >
                  {item.number}
                </button>
              );
            })}
          </div>

          <div className={styles.contentGrid}>
            <section className={styles.itemCard}>
              <h2 className={styles.itemTitle}>
                Задание {currentItem.number}: {pointsLabel(currentItem.max_points)}
              </h2>

              {currentItem.type === 'question' ? (
                <div className={styles.questionBlock}>
                  <p className={styles.promptText}>{currentItem.text}</p>
                  <ul className={styles.optionList}>
                    {currentItem.answer_options.map((option) => {
                      const isSelected = currentItem.user_answer === option;
                      const isCorrect = isSelected && currentItem.status === 'correct';
                      const isWrong = isSelected && currentItem.status !== 'correct';
                      return (
                        <li
                          key={option}
                          className={[
                            styles.optionItem,
                            isCorrect ? styles.optionItemCorrect : '',
                            isWrong ? styles.optionItemWrong : '',
                            isSelected && !isCorrect && !isWrong ? styles.optionItemSelected : '',
                          ].join(' ')}
                        >
                          <input type="radio" readOnly checked={isSelected} />
                          <span>{option}</span>
                        </li>
                      );
                    })}
                  </ul>
                  
                </div>
              ) : (
                <>
                  <p className={styles.promptText}>{taskPrompt(currentItem)}</p>
                  {isFileTask(currentItem) ? (
                    <ul className={styles.attachments}>
                      {currentItem.file_attachments.map((file) => (
                        <li key={file.attachment_id}>
                          <a href={file.file_url} target="_blank" rel="noreferrer">
                            {file.file_name}
                          </a>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <SafeHtml html={currentItem.user_answer ?? ''} className={styles.answerPreview} />
                  )}

                  <div className={styles.reviewForm}>
                    <label className={styles.fieldLabel}>
                      Количество баллов
                      <select
                        value={drafts[currentItem.answer_id]?.points ?? 0}
                        disabled={isReviewed}
                        className={styles.pointsSelect}
                        onChange={(e) => {
                          const bounded = Number(e.target.value);
                          setDrafts((prev) => ({
                            ...prev,
                            [currentItem.answer_id]: {
                              points: bounded,
                              comment: prev[currentItem.answer_id]?.comment ?? '',
                            },
                          }));
                        }}
                      >
                        {Array.from({ length: currentItem.max_points + 1 }, (_, i) => (
                          <option key={i} value={i}>{pointsLabel(i)}</option>
                        ))}
                      </select>
                    </label>
                    <div className={styles.editorWrap}>
                      <RichTextEditor
                        toolbarPosition="bottom"
                        value={drafts[currentItem.answer_id]?.comment ?? ''}
                        onChange={(html) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [currentItem.answer_id]: {
                              points: prev[currentItem.answer_id]?.points ?? 0,
                              comment: html,
                            },
                          }))
                        }
                        placeholder="Комментарий"
                        className={styles.editor}
                        disabled={isReviewed}
                      />
                    </div>
                  </div>
                </>
              )}

              <div className={styles.actions}>
                <Button type="button" variant="outline" disabled={step === 0} onClick={() => setStep((s) => Math.max(0, s - 1))}>
                  Назад
                </Button>
                {step < items.length - 1 ? (
                  <Button type="button" onClick={() => setStep((s) => s + 1)}>
                    Далее
                  </Button>
                ) : !isReviewed ? (
                  <Button
                    type="button"
                    onClick={() => setConfirmOpen(true)}
                    disabled={reviewMutation.isPending}
                  >
                    {reviewMutation.isPending ? 'Сохранение...' : 'Отправить'}
                  </Button>
                ) : null}
              </div>
            </section>

            <aside className={styles.sideCard}>
              <Link
                to={attemptsListPath}
                state={location.state}
                className={styles.backToList}
              >
                <ChevronLeft size={14} aria-hidden />
                К списку попыток
              </Link>
              <div className={styles.sideCardTitle}>{homeworkQuery.data.title}</div>
              <div className={styles.meta}>Попытка: {attemptId}</div>
              {isReviewed ? (
                <div className={styles.reviewedBadge}>Проверено</div>
              ) : (
                <div className={styles.meta}>Статус: на проверке</div>
              )}
            </aside>
          </div>
        </div>
      </div>

      <AlertDialog
        open={confirmOpen}
        onOpenChange={(open) => {
          if (!open) setConfirmOpen(false);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Отправить проверку?</AlertDialogTitle>
            <AlertDialogDescription>
              После отправки изменить оценки и комментарии будет нельзя.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={reviewMutation.isPending}>
              Отмена
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={reviewMutation.isPending}
              onClick={(event) => {
                event.preventDefault();
                reviewMutation.mutate(
                  { attempt_id: attemptId, items: reviewItems },
                  {
                    onSuccess: () => {
                      if (attemptId) clearReviewDraft(attemptId);
                      setConfirmOpen(false);
                      notifySuccess({
                        title: 'Проверка сохранена',
                        description: 'Оценки отправлены студенту.',
                      });
                      window.setTimeout(() => {
                        navigate(
                          getHomeworkReviewBackHref(location.state, courseSlug, lessonSlug),
                        );
                      }, 1000);
                    },
                  },
                );
              }}
            >
              {reviewMutation.isPending ? 'Сохранение...' : 'Отправить'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageFrame>
  );
}
