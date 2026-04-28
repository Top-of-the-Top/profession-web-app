import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  PageFrame,
  Spinner,
} from '@shared/ui';
import {
  useHomeworkAttempt,
  useHomeworkDetail,
} from '@shared/api/queries/courses';
import {
  useRequestHomeworkUpload,
  useSubmitHomeworkAttempt,
} from '@shared/api/mutations/courses';
import type {
  HomeworkAttemptAttachment,
  HomeworkAttemptTaskItem,
  SubmitHomeworkAttemptItemPayload,
} from '@shared/api/courseApi';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { notifyError, notifySuccess } from '@shared/lib/sileo/notify';
import styles from './HomeworkSubmissionPage.module.css';

const MAX_FILE_BYTES = 10 * 1024 * 1024;

function answerKey(type: 'question' | 'task', id: string): string {
  return `${type}:${id}`;
}

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
  const uploadFileMutation = useRequestHomeworkUpload(homeworkSlug ?? '');

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [attachments, setAttachments] = useState<
    Record<string, HomeworkAttemptAttachment[]>
  >({});

  useEffect(() => {
    const attempt = attemptQuery.data;
    if (!attempt) return;

    const nextAnswers: Record<string, string> = {};
    const nextAttachments: Record<string, HomeworkAttemptAttachment[]> = {};
    for (const item of attempt.items) {
      if (item.type === 'question') {
        nextAnswers[answerKey('question', item.question_id)] = item.user_answer ?? '';
      } else {
        nextAnswers[answerKey('task', item.task_id)] = item.user_answer ?? '';
        nextAttachments[answerKey('task', item.task_id)] = item.file_attachments ?? [];
      }
    }

    setAnswers(nextAnswers);
    setAttachments(nextAttachments);
  }, [attemptQuery.data]);

  const homeworkTitle = useMemo(() => {
    return detailQuery.data?.title || 'Домашнее задание';
  }, [detailQuery.data?.title]);

  const handleUploadFile = async (task: HomeworkAttemptTaskItem, file: File) => {
    if (!homeworkSlug || !attemptQuery.data) return;
    if (file.size > MAX_FILE_BYTES) {
      notifyError({
        title: 'Файл слишком большой',
        description: 'Максимальный размер файла 10MB.',
      });
      return;
    }

    const extension = normalizeFileExtension(file.name);
    try {
      const uploadData = await uploadFileMutation.mutateAsync({
        attempt_id: attemptQuery.data.attempt_id,
        task_id: task.task_id,
        file_name: file.name,
        file_size: file.size,
        file_extension: extension,
      });

      const method = uploadData.method.toUpperCase();
      if (method === 'POST') {
        const formData = new FormData();
        Object.entries(uploadData.fields).forEach(([key, value]) => {
          formData.append(key, value);
        });
        formData.append('file', file);
        const uploadResponse = await fetch(uploadData.url, {
          method: 'POST',
          body: formData,
        });
        if (!uploadResponse.ok) {
          throw new Error('Не удалось загрузить файл в хранилище.');
        }
      } else if (method === 'PUT') {
        const uploadResponse = await fetch(uploadData.url, {
          method: 'PUT',
          headers: {
            'Content-Type': file.type || 'application/octet-stream',
          },
          body: file,
        });
        if (!uploadResponse.ok) {
          throw new Error('Не удалось загрузить файл в хранилище.');
        }
      } else {
        throw new Error('Неподдерживаемый метод загрузки файла.');
      }

      const key = uploadData.fields.key ?? file.name;
      const uploadedFileUrl = key
        ? `${uploadData.url.replace(/\/$/, '')}/${key}`
        : uploadData.url;
      const taskKey = answerKey('task', task.task_id);
      const attachment: HomeworkAttemptAttachment = {
        attachment_id: key,
        file_name: file.name,
        file_url: uploadedFileUrl,
        file_size: file.size,
        file_extension: extension,
      };
      setAttachments((prev) => ({
        ...prev,
        [taskKey]: [...(prev[taskKey] ?? []), attachment],
      }));
      notifySuccess({ title: 'Файл загружен' });
    } catch (err) {
      notifyError({
        title: 'Не удалось загрузить файл',
        description: extractApiMessage(err),
      });
    }
  };

  const removeAttachment = (taskId: string, attachmentId: string) => {
    const key = answerKey('task', taskId);
    setAttachments((prev) => ({
      ...prev,
      [key]: (prev[key] ?? []).filter(
        (attachment) => attachment.attachment_id !== attachmentId,
      ),
    }));
  };

  const handleSubmit = async () => {
    const attempt = attemptQuery.data;
    if (!attempt || !homeworkSlug) return;

    const items: SubmitHomeworkAttemptItemPayload[] = attempt.items.map((item) => {
      if (item.type === 'question') {
        return {
          type: 'question',
          id: item.question_id,
          number: item.number,
          user_answer: answers[answerKey('question', item.question_id)] || null,
        };
      }
      const taskKey = answerKey('task', item.task_id);
      return {
        type: 'task',
        id: item.task_id,
        number: item.number,
        user_answer: answers[taskKey] || null,
        file_attachments: attachments[taskKey] ?? [],
      };
    });

    try {
      await submitAttempt.mutateAsync({
        homework_id: attempt.homework_id,
        attempt_id: attempt.attempt_id,
        send_at: new Date().toISOString(),
        items,
      });
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
            <Button type="button" onClick={() => navigate(-1)}>
              Назад
            </Button>
          </div>
        </div>
      </PageFrame>
    );
  }

  if (attemptQuery.isLoading || detailQuery.isLoading) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </PageFrame>
    );
  }

  if (!attemptQuery.data || attemptQuery.isError) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <div className={styles.errorBox}>
            <p className={styles.errorText}>
              Не удалось загрузить попытку для домашнего задания.
            </p>
            <div className={styles.errorActions}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Назад
              </Button>
              <Button type="button" onClick={() => void attemptQuery.refetch()}>
                Обновить
              </Button>
            </div>
          </div>
        </div>
      </PageFrame>
    );
  }

  const attempt = attemptQuery.data;
  const isDraft = attempt.status === 'draft';

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

      <div className={styles.header}>
        <h1 className={styles.title}>{homeworkTitle}</h1>
        <div className={styles.meta}>
          <span className={styles.statusBadge}>{formatAttemptStatus(attempt.status)}</span>
          <span className={styles.deadlineText}>
            Дедлайн: {new Date(attempt.deadline).toLocaleString('ru-RU')}
          </span>
        </div>
      </div>

      <div className={styles.itemsList}>
        {attempt.items.map((item) => {
          if (item.type === 'question') {
            const key = answerKey('question', item.question_id);
            const value = answers[key] ?? '';
            return (
              <section key={key} className={styles.itemCard}>
                <p className={styles.itemTitle}>
                  {item.number}. {item.text}
                </p>
                <div className={styles.optionsList}>
                  {item.answer_options.map((option) => (
                    <label key={option} className={styles.optionLabel}>
                      <input
                        type="radio"
                        name={key}
                        checked={value === option}
                        disabled={!isDraft}
                        onChange={() =>
                          setAnswers((prev) => ({ ...prev, [key]: option }))
                        }
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </section>
            );
          }

          const taskKey = answerKey('task', item.task_id);
          const value = answers[taskKey] ?? '';
          const taskAttachments = attachments[taskKey] ?? [];

          return (
            <section key={taskKey} className={styles.itemCard}>
              <p className={styles.itemTitle}>
                {item.number}. {item.text}
              </p>
              <textarea
                className={styles.answerArea}
                rows={8}
                value={value}
                disabled={!isDraft}
                onChange={(event) =>
                  setAnswers((prev) => ({ ...prev, [taskKey]: event.target.value }))
                }
                placeholder="Введите решение задачи"
              />
              <div className={styles.attachmentsBlock}>
                <label className={styles.uploadButton}>
                  <input
                    type="file"
                    disabled={!isDraft || uploadFileMutation.isPending}
                    onChange={(event) => {
                      const file = event.currentTarget.files?.[0];
                      if (!file) return;
                      void handleUploadFile(item, file);
                      event.currentTarget.value = '';
                    }}
                  />
                  Прикрепить файл
                </label>
                <ul className={styles.attachmentsList}>
                  {taskAttachments.map((attachment) => (
                    <li key={attachment.attachment_id} className={styles.attachmentItem}>
                      <span>{attachment.file_name}</span>
                      {isDraft && (
                        <button
                          type="button"
                          className={styles.removeAttachment}
                          onClick={() =>
                            removeAttachment(item.task_id, attachment.attachment_id)
                          }
                        >
                          Удалить
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          );
        })}
      </div>

      <div className={styles.actionsRow}>
        <Button type="button" variant="outline" onClick={() => navigate(-1)}>
          Назад
        </Button>
        <Button
          type="button"
          disabled={!isDraft || submitAttempt.isPending}
          onClick={() => void handleSubmit()}
        >
          {submitAttempt.isPending ? 'Отправка...' : 'Отправить ДЗ'}
        </Button>
      </div>
    </PageFrame>
  );
}
