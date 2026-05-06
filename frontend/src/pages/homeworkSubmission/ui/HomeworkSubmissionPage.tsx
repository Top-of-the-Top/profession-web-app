import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Paperclip, FileText, X, Clock, CheckCircle2 } from 'lucide-react';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  PageFrame,
  RichTextEditor,
  SafeHtml,
  Spinner,
} from '@shared/ui';
import {
  useHomeworkAttempt,
  useHomeworkDetail,
  useCourseBySlug,
  useLessonBySlug,
} from '@shared/api/queries/courses';
import { useSubmitHomeworkAttempt } from '@shared/api/mutations/courses';
import type {
  HomeworkAttemptAttachment,
  HomeworkAttemptItem,
  HomeworkDetailItem,
  SubmitHomeworkAttemptItemPayload,
} from '@shared/api/courseApi';
import { uploadMediaAsset } from '@shared/lib/uploads/uploadMediaAsset';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { notifyError, notifySuccess } from '@shared/lib/sileo/notify';
import {
  useHomeworkDraft,
  readDraft,
  clearDraft,
  fromAttachmentMeta,
} from '../lib/useHomeworkDraft';
import { HOMEWORK_FILE_TASK_TEXT_PREFIX } from '../../../features/course-builder/model/homeworkTypes';
import styles from './HomeworkSubmissionPage.module.css';

function normalizeFileExtension(fileName: string): string {
  const parts = fileName.trim().split('.');
  if (parts.length < 2) return '';
  return parts[parts.length - 1].toLowerCase();
}

function extractApiMessage(err: unknown): string {
  const parsed = parseApiError(err);
  if (!parsed) {
    return err instanceof Error ? err.message : 'Попробуйте снова позже.';
  }
  const body = parsed.body as {
    message?: unknown;
    details?: { items?: Array<{ issue?: unknown }> };
  };
  if (typeof body?.message === 'string' && body.message.trim()) {
    return body.message;
  }
  const issue = body?.details?.items?.[0]?.issue;
  if (typeof issue === 'string' && issue.trim()) {
    return issue;
  }
  return `Ошибка запроса (${parsed.status})`;
}

function formatAnswerHtml(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '<p>Ответ не заполнен</p>';
  return trimmed;
}

function formatPointsLabel(points: number): string {
  const mod10 = points % 10;
  const mod100 = points % 100;
  if (mod10 === 1 && mod100 !== 11) return `${points} балл`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${points} балла`;
  }
  return `${points} баллов`;
}

function isHomeworkFileTask(item: HomeworkDetailItem): boolean {
  return (
    item.type === 'task' &&
    (item.text ?? '').startsWith(HOMEWORK_FILE_TASK_TEXT_PREFIX)
  );
}

function homeworkTaskPromptText(item: HomeworkDetailItem & { type: 'task' }): string {
  const raw = item.text ?? '';
  if (raw.startsWith(HOMEWORK_FILE_TASK_TEXT_PREFIX)) {
    return raw.slice(HOMEWORK_FILE_TASK_TEXT_PREFIX.length);
  }
  return raw;
}

type ItemStatus = 'correct' | 'incorrect' | 'partily' | string;

function statusLabel(s: ItemStatus): string {
  if (s === 'correct') return 'Верно';
  if (s === 'incorrect') return 'Неверно';
  if (s === 'partily') return 'Частично верно';
  return '';
}

function statusBadgeClass(s: ItemStatus): string {
  if (s === 'correct') return styles.statusBadgeCorrect;
  if (s === 'partily') return styles.statusBadgePartial;
  if (s === 'incorrect') return styles.statusBadgeIncorrect;
  return '';
}

/* Donut chart for side card */
function DonutScore({ score, max }: { score: number; max: number }) {
  const r = 44;
  const cx = 56;
  const cy = 56;
  const circumference = 2 * Math.PI * r;
  const pct = max > 0 ? Math.min(score / max, 1) : 0;
  const dash = pct * circumference;
  const gap = circumference - dash;

  return (
    <div className={styles.donutWrap}>
      <svg width={112} height={112} viewBox="0 0 112 112">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e4e7ec" strokeWidth={10} />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke="#22c55e" strokeWidth={10}
          strokeDasharray={`${dash} ${gap}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      </svg>
      <div className={styles.donutCenter}>
        <span className={styles.donutScore}>{score}</span>
        <span className={styles.donutMax}>из {max}</span>
      </div>
    </div>
  );
}

export default function HomeworkSubmissionPage() {
  const { slug: courseSlug, lessonSlug, homeworkSlug } = useParams<{
    slug: string;
    lessonSlug: string;
    homeworkSlug: string;
  }>();
  const navigate = useNavigate();
  const attemptQuery = useHomeworkAttempt(courseSlug, homeworkSlug);
  const detailQuery = useHomeworkDetail(courseSlug, lessonSlug, homeworkSlug);
  const courseQuery = useCourseBySlug(courseSlug);
  const lessonQuery = useLessonBySlug(courseSlug, lessonSlug);
  const submitAttempt = useSubmitHomeworkAttempt(courseSlug ?? '', homeworkSlug ?? '');

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attachments, setAttachments] = useState<Record<string, HomeworkAttemptAttachment[]>>({});
  const [uploadProgress, setUploadProgress] = useState<
    Record<string, { phase: string; percent: number; fileName: string } | null>
  >({});
  const [answered, setAnswered] = useState<Set<string>>(new Set());
  const [currentItemIndex, setCurrentItemIndex] = useState(0);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const [slideDir, setSlideDir] = useState<'left' | 'right' | null>(null);
  const animationKey = useRef(0);

  const { persist, persistDebounced } = useHomeworkDraft(homeworkSlug);

  const { persist, persistDebounced } = useHomeworkDraft(homeworkSlug);

  useEffect(() => {
    const attempt = attemptQuery.data;
    if (!attempt) return;

    if (attempt.status !== 'draft' && homeworkSlug) {
      clearDraft(homeworkSlug);
    }

    const serverAnswers: Record<string, string> = {};
    const serverAttachments: Record<string, HomeworkAttemptAttachment[]> = {};
    for (const item of attempt.items) {
      const id = item.type === 'question' ? item.question_id : item.task_id;
      if (!id) continue;
      serverAnswers[id] = item.user_answer ?? '';
      if (item.type === 'task') {
        serverAttachments[id] = item.file_attachments ?? [];
      }
    }

    if (attempt.status === 'draft' && homeworkSlug) {
      const draft = readDraft(homeworkSlug);
      if (draft) {
        setAnswers({ ...serverAnswers, ...draft.answers });
        setAttachments({ ...serverAttachments, ...fromAttachmentMeta(draft.attachments) });
        setCurrentItemIndex(0);
        return;
      }
    }

    setAnswers(serverAnswers);
    setAttachments(serverAttachments);
    setCurrentItemIndex(0);
  }, [attemptQuery.data, homeworkSlug]);

  const homeworkTitle = useMemo(
    () => detailQuery.data?.title || 'Домашнее задание',
    [detailQuery.data?.title],
  );
  const courseTitle = useMemo(
    () => courseQuery.data?.title || 'Курс',
    [courseQuery.data?.title],
  );
  const lessonTitle = useMemo(
    () => lessonQuery.data?.title || 'Урок',
    [lessonQuery.data?.title],
  );

  const handleUploadFile = async (item: HomeworkDetailItem, file: File) => {
    if (!homeworkSlug || !attemptQuery.data) return;
    const extension = normalizeFileExtension(file.name);
    setUploadProgress((prev) => ({
      ...prev,
      [item.id]: { phase: 'initiating', percent: 0, fileName: file.name },
    }));
    try {
      const uploaded = await uploadMediaAsset('homework_attachment', file, {
        onProgress: (event) => {
          setUploadProgress((prev) => ({
            ...prev,
            [item.id]: {
              phase: event.phase,
              percent: event.progressPercent ?? (event.phase === 'polling' ? 99 : 0),
              fileName: file.name,
            },
          }));
        },
      });
      const attachment: HomeworkAttemptAttachment = {
        attachment_id: uploaded.assetId,
        file_name: file.name,
        file_url: '',
        file_size: file.size,
        file_extension: extension,
      };
      const nextAttachments = {
        ...attachments,
        [item.id]: [...(attachments[item.id] ?? []), attachment],
      };
      setAttachments(nextAttachments);
      persist(answers, nextAttachments);
      setAnswered((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    } catch (err) {
      notifyError({
        title: 'Не удалось загрузить файл',
        description: extractApiMessage(err),
      });
    } finally {
      setUploadProgress((prev) => ({ ...prev, [item.id]: null }));
    }
  };

  const removeAttachment = (itemId: string, attachmentId: string) => {
    const nextAttachments = {
      ...attachments,
      [itemId]: (attachments[itemId] ?? []).filter((a) => a.attachment_id !== attachmentId),
    };
    setAttachments(nextAttachments);
    persist(answers, nextAttachments);
    setAnswered((prev) => {
      const next = new Set(prev);
      next.delete(itemId);
      return next;
    });
  };

  const handleSubmit = async () => {
    const attempt = attemptQuery.data;
    const detail = detailQuery.data;
    if (!attempt || !detail || !homeworkSlug) return;

    const items: SubmitHomeworkAttemptItemPayload[] = attempt.items.map((attemptItem) => {
      if (attemptItem.type === 'question') {
        return {
          type: 'question',
          id: attemptItem.question_id,
          number: attemptItem.number,
          user_answer: answers[attemptItem.question_id] || null,
        };
      }
      return {
        type: 'task',
        id: attemptItem.task_id,
        number: attemptItem.number,
        user_answer: answers[attemptItem.task_id] || null,
        asset_ids: (attachments[attemptItem.task_id] ?? []).map((a) => a.attachment_id),
      };
    });

    try {
      await submitAttempt.mutateAsync({
        homework_id: attempt.homework_id,
        attempt_id: attempt.attempt_id,
        send_at: new Date().toISOString(),
        items,
      });
      clearDraft(homeworkSlug);
      notifySuccess({
        title: 'Домашнее задание отправлено',
        description: 'Ожидайте проверку преподавателем.',
      });
      window.setTimeout(() => {
        navigate(`/app/courses/${courseSlug}/${lessonSlug}`);
      }, 1000);
    } catch (err) {
      notifyError({
        title: 'Не удалось отправить ДЗ',
        description: extractApiMessage(err),
      });
    }
  };

  const animateTo = (index: number) => {
    if (index === currentItemIndex) return;
    const dir = index > currentItemIndex ? 'left' : 'right';
    setSlideDir(dir);
    animationKey.current += 1;
    setCurrentItemIndex(index);
    setTimeout(() => setSlideDir(null), 320);
  };

  if (!courseSlug || !lessonSlug || !homeworkSlug) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>Некорректный адрес задания.</p>
            <Button type="button" onClick={() => navigate(-1)}>Назад</Button>
          </div>
        </div>
      </PageFrame>
    );
  }

  // Derive these before any conditional returns so hooks are always called in the same order
  const attempt = attemptQuery.data ?? null;
  const detail = detailQuery.data ?? null;
  const items = detail?.items ?? [];
  const isDraft = attempt?.status === 'draft';
  const isReviewed = attempt?.status === 'reviewed';

  // Map detail item id → attempt item status (for bubble coloring in reviewed mode)
  const itemStatusMap = useMemo<Map<string, ItemStatus>>(() => {
    if (!isReviewed || !attempt) return new Map();
    const map = new Map<string, ItemStatus>();
    for (const ai of attempt.items) {
      const id = ai.type === 'question' ? ai.question_id : ai.task_id;
      if (id) map.set(id, ai.status ?? '');
    }
    return map;
  }, [isReviewed, attempt]);

  if (attemptQuery.isLoading || detailQuery.isLoading) {
    return (
      <PageFrame>
        <div className={styles.centered}><Spinner /></div>
      </PageFrame>
    );
  }

  if (!attemptQuery.data || attemptQuery.isError) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>Не удалось загрузить попытку для домашнего задания.</p>
            <div className={styles.errorActions}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>Назад</Button>
              <Button type="button" onClick={() => void attemptQuery.refetch()}>Обновить</Button>
            </div>
          </div>
        </div>
      </PageFrame>
    );
  }

  if (!detailQuery.data || detailQuery.isError) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>Не удалось загрузить задания.</p>
            <div className={styles.errorActions}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>Назад</Button>
              <Button type="button" onClick={() => void detailQuery.refetch()}>Обновить</Button>
            </div>
          </div>
        </div>
      </PageFrame>
    );
  }

  // After guards, attempt is guaranteed non-null
  const safeAttempt = attemptQuery.data!;

  if (items.length === 0) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>В этом домашнем задании пока нет вопросов.</p>
            <Button type="button" onClick={() => navigate(-1)}>Назад</Button>
          </div>
        </div>
      </PageFrame>
    );
  }

  const currentItem = items[currentItemIndex];
  const currentPromptText =
    currentItem.type === 'question'
      ? currentItem.text
      : homeworkTaskPromptText(currentItem as HomeworkDetailItem & { type: 'task' });
  const currentIsFileTask =
    currentItem.type === 'task' && isHomeworkFileTask(currentItem);
  const currentItemPoints = currentItem.max_points ?? 0;

  // Find attempt item for current detail item (for status/review)
  const currentAttemptItem: HomeworkAttemptItem | undefined = safeAttempt.items.find((ai) =>
    ai.type === 'question'
      ? ai.question_id === currentItem.id
      : ai.task_id === currentItem.id,
  );
  const currentStatus: ItemStatus = currentAttemptItem?.status ?? '';

  // Per-item result points (for reviewed state)
  function itemResultPoints(attemptItem: HomeworkAttemptItem): number | null {
    if (!isReviewed) return null;
    if (attemptItem.type === 'question') {
      return attemptItem.status === 'correct' ? attemptItem.max_points : 0;
    }
    return attemptItem.review?.points ?? null;
  }

  const currentResultPoints = currentAttemptItem ? itemResultPoints(currentAttemptItem) : null;

  const allAnswered = items.every((item) => answered.has(item.id));

  const handleAnswerCurrent = () => {
    setAnswered((prev) => new Set([...prev, currentItem.id]));
    const nextIndex = currentItemIndex < items.length - 1 ? currentItemIndex + 1 : currentItemIndex;
    if (nextIndex !== currentItemIndex) animateTo(nextIndex);
  };

  const slideClass =
    slideDir === 'left'
      ? styles.slideInLeft
      : slideDir === 'right'
        ? styles.slideInRight
        : '';

  return (
    <PageFrame>
      {showConfirmDialog && (
        <div className={styles.dialogOverlay}>
          <div className={styles.dialog}>
            <p className={styles.dialogText}>
              Уверены, что хотите отправить домашнее задание? После отправки изменить ответы будет нельзя.
            </p>
            <div className={styles.dialogActions}>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowConfirmDialog(false)}
              >
                Отмена
              </Button>
              <Button
                type="button"
                disabled={submitAttempt.isPending}
                onClick={async () => {
                  setShowConfirmDialog(false);
                  await handleSubmit();
                }}
              >
                {submitAttempt.isPending ? 'Отправка...' : 'Отправить'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className={styles.pageRoot}>
        <div className={styles.breadcrumbWrap}>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to={`/app/courses/${courseSlug}`}>{courseTitle}</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link to={`/app/courses/${courseSlug}/${lessonSlug}`}>{lessonTitle}</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{homeworkTitle}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </div>

        <div className={styles.centeredColumn}>
          {safeAttempt.status === 'submitted' && (
            <div className={styles.statusBannerSubmitted}>
              <Clock size={16} className={styles.statusBannerIcon} />
              <span>Работа отправлена и ожидает проверки преподавателем. Редактирование недоступно.</span>
            </div>
          )}

          <div className={styles.topNav}>
            <button
              type="button"
              className={styles.stepArrow}
              disabled={currentItemIndex === 0}
              onClick={() => animateTo(currentItemIndex - 1)}
            >
              <ChevronLeft size={18} />
            </button>
            <div className={styles.stepsRow}>
              {items.map((item, index) => {
                const isActive = index === currentItemIndex;
                const isAnswered = answered.has(item.id);
                const reviewedStatus = itemStatusMap.get(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={[
                      styles.stepButton,
                      isActive ? styles.stepButtonActive : '',
                      !isActive && isAnswered ? styles.stepButtonAnswered : '',
                      !isActive && reviewedStatus === 'correct' ? styles.stepButtonCorrect : '',
                      !isActive && (reviewedStatus === 'incorrect' || reviewedStatus === 'partily') ? styles.stepButtonIncorrect : '',
                    ].join(' ')}
                    onClick={() => animateTo(index)}
                  >
                    {index + 1}
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              className={styles.stepArrow}
              disabled={currentItemIndex === items.length - 1}
              onClick={() => animateTo(currentItemIndex + 1)}
            >
              <ChevronRight size={18} />
            </button>
          </div>

          <div className={styles.contentGrid}>
            <section
              key={animationKey.current}
              className={[
                styles.itemCard,
                !isDraft ? styles.itemCardReadOnly : '',
                slideClass,
              ].join(' ')}
            >
              {/* Header row: "Задание N: X баллов" + status badge */}
              <div className={styles.itemMetaRow}>
                <p className={styles.itemMeta}>
                  Задание {currentItemIndex + 1}: {formatPointsLabel(currentItemPoints)}
                </p>
                {isReviewed && currentStatus && statusLabel(currentStatus) && (
                  <span className={[styles.statusBadge, statusBadgeClass(currentStatus)].join(' ')}>
                    {statusLabel(currentStatus)}
                  </span>
                )}
              </div>

              <p className={styles.itemTitle}>{currentPromptText}</p>

              {currentItem.type === 'question' ? (
                <div className={styles.optionsList}>
                  {(currentItem.answer_options ?? []).map((option) => {
                    const userAnswer = isReviewed && currentAttemptItem?.type === 'question'
                      ? currentAttemptItem.user_answer
                      : answers[currentItem.id] ?? null;
                    const isSelected = userAnswer === option;
                    const correctAns = currentAttemptItem?.type === 'question' ? currentAttemptItem.correct_ans : null;
                    const isCorrectOption = isReviewed && correctAns === option;
                    const isWrongSelected = isReviewed && isSelected && !isCorrectOption;
                    return (
                      <label
                        key={option}
                        className={[
                          styles.optionLabel,
                          !option.trim() ? styles.optionLabelEmpty : '',
                          isSelected && !isReviewed ? styles.optionLabelSelected : '',
                          isCorrectOption ? styles.optionLabelCorrect : '',
                          isWrongSelected ? styles.optionLabelWrong : '',
                        ].join(' ')}
                      >
                        <input
                          type="radio"
                          name={currentItem.id}
                          checked={isSelected}
                          disabled={!isDraft}
                          onChange={() => {
                            const nextAnswers = { ...answers, [currentItem.id]: option };
                            setAnswers(nextAnswers);
                            persist(nextAnswers, attachments);
                            setAnswered((prev) => {
                              const next = new Set(prev);
                              next.delete(currentItem.id);
                              return next;
                            });
                          }}
                        />
                        <span>{option}</span>
                      </label>
                    );
                  })}
                </div>
              ) : currentIsFileTask ? (
                <div className={styles.taskAnswerWrap}>
                  {isReviewed && <p className={styles.answerLabel}>Ваш ответ</p>}
                  <div className={styles.attachmentsBlock}>
                    {isDraft && (
                      <label className={styles.uploadButton}>
                        <input
                          type="file"
                          disabled={!isDraft || uploadProgress[currentItem.id] != null}
                          onChange={(event) => {
                            const file = event.currentTarget.files?.[0];
                            if (!file) return;
                            void handleUploadFile(currentItem, file);
                            event.currentTarget.value = '';
                          }}
                        />
                        <Paperclip size={14} />
                        Прикрепить файл
                      </label>
                    )}
                    <ul className={styles.attachmentsList}>
                      {(attachments[currentItem.id] ?? []).map((attachment) => (
                        <li key={attachment.attachment_id} className={styles.attachmentItem}>
                          <div className={styles.attachmentThumb}>
                            <FileText size={28} className={styles.attachmentThumbIcon} />
                          </div>
                          <span className={styles.attachmentName}>{attachment.file_name}</span>
                          {isDraft && (
                            <button
                              type="button"
                              className={styles.removeAttachment}
                              onClick={() =>
                                removeAttachment(currentItem.id, attachment.attachment_id)
                              }
                            >
                              <X size={10} />
                            </button>
                          )}
                        </li>
                      ))}
                      {uploadProgress[currentItem.id] != null && (() => {
                        const p = uploadProgress[currentItem.id]!;
                        const isIndeterminate = p.phase === 'initiating' || p.phase === 'polling';
                        return (
                          <li className={styles.attachmentItemUploading}>
                            <div className={styles.attachmentThumbUploading}>
                              <FileText size={24} className={styles.attachmentThumbIcon} />
                            </div>
                            <span className={styles.attachmentName}>{p.fileName}</span>
                            <div className={styles.uploadProgressBar}>
                              <div
                                className={[
                                  styles.uploadProgressFill,
                                  isIndeterminate ? styles.uploadProgressIndeterminate : '',
                                ].join(' ')}
                                style={isIndeterminate ? undefined : { width: `${p.percent}%` }}
                              />
                            </div>
                          </li>
                        );
                      })()}
                    </ul>
                  </div>

                  {/* Teacher comment for file task in reviewed state */}
                  {isReviewed && currentAttemptItem?.type === 'task' && currentAttemptItem.review?.comment && (
                    <div className={styles.reviewComment}>
                      <div className={styles.reviewCommentHeader}>
                        <div className={styles.reviewerAvatar}>
                          {currentAttemptItem.review.reviewer?.first_name?.[0] ?? '?'}
                        </div>
                        <span className={styles.reviewerName}>
                          {currentAttemptItem.review.reviewer
                            ? `${currentAttemptItem.review.reviewer.first_name} ${currentAttemptItem.review.reviewer.last_name}`
                            : 'Преподаватель'}
                          <span className={styles.reviewerRole}> · Преподаватель</span>
                        </span>
                      </div>
                      <SafeHtml className={styles.reviewCommentText} html={currentAttemptItem.review.comment ?? ''} />
                    </div>
                  )}
                </div>
              ) : (
                <div className={`${styles.taskAnswerWrap} ${styles.taskTextAnswerWrap}`}>
                  {isReviewed && <p className={styles.answerLabel}>Ваш ответ</p>}
                  {isDraft ? (
                    <div className={styles.answerEditorWrap}>
                      <RichTextEditor
                        key={currentItem.id}
                        className={styles.answerEditor}
                        toolbarPosition="bottom"
                        value={answers[currentItem.id] ?? ''}
                        onChange={(html) => {
                          const nextAnswers = { ...answers, [currentItem.id]: html };
                          setAnswers(nextAnswers);
                          persistDebounced(nextAnswers, attachments);
                          setAnswered((prev) => {
                            const next = new Set(prev);
                            next.delete(currentItem.id);
                            return next;
                          });
                        }}
                        placeholder="Введите ответ"
                      />
                    </div>
                  ) : (
                    <SafeHtml
                      className={`${styles.answerPreview} ${styles.answerPreviewBounded}`}
                      html={formatAnswerHtml(answers[currentItem.id] ?? '')}
                    />
                  )}

                  {/* Teacher comment for text task in reviewed state */}
                  {isReviewed && currentAttemptItem?.type === 'task' && currentAttemptItem.review?.comment && (
                    <div className={styles.reviewComment}>
                      <div className={styles.reviewCommentHeader}>
                        <div className={styles.reviewerAvatar}>
                          {currentAttemptItem.review.reviewer?.first_name?.[0] ?? '?'}
                        </div>
                        <span className={styles.reviewerName}>
                          {currentAttemptItem.review.reviewer
                            ? `${currentAttemptItem.review.reviewer.first_name} ${currentAttemptItem.review.reviewer.last_name}`
                            : 'Преподаватель'}
                          <span className={styles.reviewerRole}> · Преподаватель</span>
                        </span>
                      </div>
                      <SafeHtml className={styles.reviewCommentText} html={currentAttemptItem.review.comment ?? ''} />
                    </div>
                  )}
                </div>
              )}

              {/* Result row at bottom */}
              {isReviewed && currentResultPoints !== null && (
                <div className={styles.resultRow}>
                  <span className={styles.resultLabel}>Результат:</span>
                  <span className={[
                    styles.resultPoints,
                    currentResultPoints === 0 ? styles.resultPointsZero : styles.resultPointsPositive,
                  ].join(' ')}>
                    {currentResultPoints} / {currentItemPoints}
                  </span>
                  <span className={styles.resultPointsUnit}>
                    {formatPointsLabel(currentItemPoints).replace(/^\d+\s*/, '')}
                  </span>
                </div>
              )}

              {isDraft && (
                <div className={styles.answerActionRow}>
                  <Button
                    type="button"
                    disabled={
                      answered.has(currentItem.id) ||
                      uploadProgress[currentItem.id] != null
                    }
                    onClick={handleAnswerCurrent}
                  >
                    {uploadProgress[currentItem.id] != null
                      ? 'Загрузка...'
                      : currentItem.type === 'question'
                        ? 'Ответить'
                        : 'Далее'}
                  </Button>
                </div>
              )}
            </section>

            <aside className={styles.sideCard}>
              <button type="button" className={styles.backToList} onClick={() => navigate(-1)}>
                <ChevronLeft size={14} />
                К списку домашних заданий
              </button>
              <div className={styles.sideCardTitle}>{homeworkTitle}</div>

              {/* Donut score for reviewed */}
              {isReviewed && safeAttempt.score != null && safeAttempt.max_points != null && (
                <DonutScore score={safeAttempt.score} max={safeAttempt.max_points} />
              )}
              {isReviewed && (safeAttempt.score != null || safeAttempt.max_points != null) && (
                <p className={styles.donutLabel}>баллов</p>
              )}

              {!isReviewed && (
                <div className={styles.meta}>
                  <span className={styles.deadlineText}>
                    Дедлайн: {new Date(safeAttempt.deadline).toLocaleString('ru-RU')}
                  </span>
                </div>
              )}

              {isDraft ? (
                <div className={styles.sideActions}>
                  <Button
                    type="button"
                    disabled={!allAnswered || submitAttempt.isPending}
                    onClick={() => setShowConfirmDialog(true)}
                  >
                    {submitAttempt.isPending ? 'Отправка...' : 'Завершить'}
                  </Button>
                </div>
              ) : safeAttempt.status === 'submitted' ? (
                <div className={styles.sideStatusChip} data-status="submitted">
                  <Clock size={13} />
                  На проверке
                </div>
              ) : safeAttempt.status === 'reviewed' ? (
                <div className={styles.sideStatusChip} data-status="reviewed">
                  <CheckCircle2 size={13} />
                  Проверено
                </div>
              ) : null}
            </aside>
          </div>
        </div>
      </div>
    </PageFrame>
  );
}
