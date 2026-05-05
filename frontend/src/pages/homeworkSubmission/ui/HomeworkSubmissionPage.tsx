import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Paperclip, FileText, X } from 'lucide-react';
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
} from '@shared/api/queries/courses';
import { useSubmitHomeworkAttempt } from '@shared/api/mutations/courses';
import type {
  HomeworkAttemptAttachment,
  HomeworkDetailItem,
  SubmitHomeworkAttemptItemPayload,
} from '@shared/api/courseApi';
import { uploadMediaAsset } from '@shared/lib/uploads/uploadMediaAsset';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { notifyError } from '@shared/lib/sileo/notify';
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

function formatAttemptStatus(status: string): string {
  if (status === 'submitted') return 'Отправлено';
  if (status === 'reviewed') return 'Проверено';
  return 'Черновик';
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

export default function HomeworkSubmissionPage() {
  const { slug: courseSlug, lessonSlug, homeworkSlug } = useParams<{
    slug: string;
    lessonSlug: string;
    homeworkSlug: string;
  }>();
  const navigate = useNavigate();
  const attemptQuery = useHomeworkAttempt(homeworkSlug);
  const detailQuery = useHomeworkDetail(courseSlug, lessonSlug, homeworkSlug);
  const submitAttempt = useSubmitHomeworkAttempt(homeworkSlug ?? '');

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attachments, setAttachments] = useState<Record<string, HomeworkAttemptAttachment[]>>({});
  const [uploadProgress, setUploadProgress] = useState<
    Record<string, { phase: string; percent: number; fileName: string } | null>
  >({});
  const [currentItemIndex, setCurrentItemIndex] = useState(0);

  const { persist, persistDebounced } = useHomeworkDraft(homeworkSlug);

  // Seed state from attempt + merge saved draft on top
  useEffect(() => {
    const attempt = attemptQuery.data;
    if (!attempt) return;

    // Clear draft when attempt is already submitted/reviewed
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
        // Draft is newer than server state — merge on top
        setAnswers({ ...serverAnswers, ...draft.answers });
        setAttachments({
          ...serverAttachments,
          ...fromAttachmentMeta(draft.attachments),
        });
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
  };

  const handleSubmit = async () => {
    const attempt = attemptQuery.data;
    const detail = detailQuery.data;
    if (!attempt || !detail || !homeworkSlug) return;

    const items: SubmitHomeworkAttemptItemPayload[] = detail.items.map((item) => {
      if (item.type === 'question') {
        return {
          type: 'question',
          id: item.id,
          number: item.number,
          user_answer: answers[item.id] || null,
        };
      }
      return {
        type: 'task',
        id: item.id,
        number: item.number,
        user_answer: answers[item.id] || null,
        asset_ids: (attachments[item.id] ?? []).map((a) => a.attachment_id),
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
      await attemptQuery.refetch();
    } catch (err) {
      notifyError({
        title: 'Не удалось отправить ДЗ',
        description: extractApiMessage(err),
      });
    }
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

  const attempt = attemptQuery.data;
  const detail = detailQuery.data;
  const items = detail.items;
  const isDraft = attempt.status === 'draft';

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
  const isLastItem = currentItemIndex === items.length - 1;

  const moveToItem = (index: number) => {
    if (index < 0 || index >= items.length) return;
    setCurrentItemIndex(index);
  };

  const handleAnswerCurrent = async () => {
    if (isLastItem) {
      await handleSubmit();
      return;
    }
    setCurrentItemIndex((prev) => Math.min(prev + 1, items.length - 1));
  };

  return (
    <PageFrame>
      <div className={styles.breadcrumbWrap}>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to={`/app/courses/${courseSlug}`}>Курс</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to={`/app/courses/${courseSlug}/${lessonSlug}`}>Урок</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{homeworkTitle}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className={styles.topNav}>
        <button
          type="button"
          className={styles.stepArrow}
          disabled={currentItemIndex === 0}
          onClick={() => moveToItem(currentItemIndex - 1)}
        >
          <ChevronLeft size={18} />
        </button>
        <div className={styles.stepsRow}>
          {items.map((item, index) => (
            <button
              key={item.id}
              type="button"
              className={`${styles.stepButton} ${
                index === currentItemIndex ? styles.stepButtonActive : ''
              }`}
              onClick={() => moveToItem(index)}
            >
              {item.number}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={styles.stepArrow}
          disabled={currentItemIndex === items.length - 1}
          onClick={() => moveToItem(currentItemIndex + 1)}
        >
          <ChevronRight size={18} />
        </button>
      </div>

      <div className={styles.contentGrid}>
        <section className={styles.itemCard}>
          <p className={styles.itemMeta}>
            Задание {currentItem.number}: {currentItem.max_points ?? 0} балла
          </p>
          <p className={styles.itemTitle}>{currentPromptText}</p>

          {currentItem.type === 'question' ? (
            <div className={styles.optionsList}>
              {(currentItem.answer_options ?? []).map((option) => (
                <label
                  key={option}
                  className={`${styles.optionLabel} ${
                    answers[currentItem.id] === option ? styles.optionLabelSelected : ''
                  }`}
                >
                  <input
                    type="radio"
                    name={currentItem.id}
                    checked={answers[currentItem.id] === option}
                    disabled={!isDraft}
                    onChange={() => {
                      const nextAnswers = { ...answers, [currentItem.id]: option };
                      setAnswers(nextAnswers);
                      persist(nextAnswers, attachments);
                    }}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
          ) : currentIsFileTask ? (
            <div className={styles.taskAnswerWrap}>
              <div className={styles.attachmentsBlock}>
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
                            className={`${styles.uploadProgressFill} ${isIndeterminate ? styles.uploadProgressIndeterminate : ''}`}
                            style={isIndeterminate ? undefined : { width: `${p.percent}%` }}
                          />
                        </div>
                      </li>
                    );
                  })()}
                </ul>
              </div>
            </div>
          ) : (
            <div className={`${styles.taskAnswerWrap} ${styles.taskTextAnswerWrap}`}>
              {isDraft ? (
                <RichTextEditor
                  key={currentItem.id}
                  className={styles.answerEditor}
                  toolbarPosition="bottom"
                  value={answers[currentItem.id] ?? ''}
                  onChange={(html) => {
                    const nextAnswers = { ...answers, [currentItem.id]: html };
                    setAnswers(nextAnswers);
                    persistDebounced(nextAnswers, attachments);
                  }}
                  placeholder="Введите ответ"
                />
              ) : (
                <SafeHtml
                  className={styles.answerPreview}
                  html={formatAnswerHtml(answers[currentItem.id] ?? '')}
                />
              )}
            </div>
          )}

          <div className={styles.answerActionRow}>
            <Button
              type="button"
              disabled={!isDraft || submitAttempt.isPending}
              onClick={() => void handleAnswerCurrent()}
            >
              {submitAttempt.isPending
                ? 'Отправка...'
                : isLastItem
                  ? 'Отправить'
                  : 'Ответить'}
            </Button>
          </div>
        </section>

        <aside className={styles.sideCard}>
          <button type="button" className={styles.backToList} onClick={() => navigate(-1)}>
            <ChevronLeft size={14} />
            К списку домашних заданий
          </button>
          <div className={styles.sideCardTitle}>{homeworkTitle}</div>
          <div className={styles.meta}>
            <span className={styles.statusBadge}>{formatAttemptStatus(attempt.status)}</span>
            <span className={styles.deadlineText}>
              Дедлайн: {new Date(attempt.deadline).toLocaleString('ru-RU')}
            </span>
          </div>
          <div className={styles.sideActions}>
            <Button
              type="button"
              disabled={!isDraft || submitAttempt.isPending}
              onClick={() => void handleSubmit()}
            >
              Завершить
            </Button>
          </div>
        </aside>
      </div>
    </PageFrame>
  );
}
