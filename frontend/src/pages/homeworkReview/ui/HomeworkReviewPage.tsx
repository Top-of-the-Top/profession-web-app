import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft } from 'lucide-react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Button, PageFrame, RichTextEditor, SafeHtml, Spinner } from '@shared/ui';
import { getHomeworkReviewBackHref } from '@shared/lib/homeworkReviewNavigation';
import { useReviewHomeworkAttempt } from '@shared/api/mutations/courses';
import { useHomeworkAttemptForReview, useHomeworkDetail } from '@shared/api/queries/courses';
import { HOMEWORK_FILE_TASK_TEXT_PREFIX } from '../../../features/course-builder/model/homeworkTypes';
import type { HomeworkAttemptTaskItem, ReviewHomeworkAttemptItemPayload } from '@shared/api/courseApi';
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
  const { slug: courseSlug, lessonSlug, homeworkSlug, attemptId } = useParams<{
    slug: string;
    lessonSlug: string;
    homeworkSlug: string;
    attemptId: string;
  }>();

  const attemptQuery = useHomeworkAttemptForReview(courseSlug, attemptId);
  const homeworkQuery = useHomeworkDetail(courseSlug, lessonSlug, homeworkSlug);
  const reviewMutation = useReviewHomeworkAttempt(courseSlug ?? '', attemptId ?? '');

  const items = attemptQuery.data?.items ?? [];
  const [step, setStep] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, ReviewDraft>>({});

  useEffect(() => {
    if (!attemptQuery.data) return;
    const nextDrafts: Record<string, ReviewDraft> = {};
    for (const item of attemptQuery.data.items) {
      if (item.type !== 'task') continue;
      nextDrafts[item.answer_id] = {
        points: item.review?.points ?? 0,
        comment: item.review?.comment ?? '',
      };
    }
    setDrafts(nextDrafts);
  }, [attemptQuery.data]);

  const currentItem = items[step];
  const isReviewed = attemptQuery.data?.status === 'reviewed';

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
            {items.map((item, idx) => (
              <button
                key={item.type === 'task' ? item.task_id : item.question_id}
                type="button"
                className={idx === step ? styles.stepActive : styles.step}
                onClick={() => setStep(idx)}
              >
                {item.number}
              </button>
            ))}
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
                    {currentItem.answer_options.map((option) => (
                      <li key={option} className={styles.optionItem}>
                        <input type="radio" readOnly checked={currentItem.user_answer === option} />
                        <span>{option}</span>
                      </li>
                    ))}
                  </ul>
                  <div className={styles.autoChecked}>
                    Автопроверка: {currentItem.status === 'correct' ? 'верно' : 'неверно'}
                  </div>
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
                      <input
                        type="number"
                        min={0}
                        max={currentItem.max_points}
                        value={drafts[currentItem.answer_id]?.points ?? 0}
                        disabled={isReviewed}
                        onChange={(e) => {
                          const parsed = Number(e.target.value);
                          const next = Number.isFinite(parsed) ? parsed : 0;
                          const bounded = Math.max(0, Math.min(currentItem.max_points, next));
                          setDrafts((prev) => ({
                            ...prev,
                            [currentItem.answer_id]: {
                              points: bounded,
                              comment: prev[currentItem.answer_id]?.comment ?? '',
                            },
                          }));
                        }}
                      />
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
                <Button
                  type="button"
                  onClick={() => {
                    if (step < items.length - 1) {
                      setStep((s) => s + 1);
                      return;
                    }
                    if (isReviewed) return;
                    reviewMutation.mutate({
                      attempt_id: attemptId,
                      items: reviewItems,
                    });
                  }}
                  disabled={reviewMutation.isPending}
                >
                  {step < items.length - 1 ? 'Далее' : reviewMutation.isPending ? 'Сохранение...' : 'Отправить'}
                </Button>
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
              <div className={styles.meta}>
                Статус: {attemptQuery.data.status === 'reviewed' ? 'проверено' : 'на проверке'}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </PageFrame>
  );
}
