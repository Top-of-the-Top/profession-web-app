import { Link, useParams } from 'react-router-dom';
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator, Button, PageFrame, Spinner } from '@shared/ui';
import { useHomeworkAttemptsByCourse } from '@shared/api/queries/courses';
import styles from './HomeworkReviewAttemptsPage.module.css';

function formatDate(value: string | null): string {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('ru-RU');
  } catch {
    return value;
  }
}

export default function HomeworkReviewAttemptsPage() {
  const { slug: courseSlug, lessonSlug, homeworkSlug } = useParams<{
    slug: string;
    lessonSlug: string;
    homeworkSlug: string;
  }>();

  const attemptsQuery = useHomeworkAttemptsByCourse(courseSlug);

  if (!courseSlug || !lessonSlug || !homeworkSlug) {
    return (
      <PageFrame>
        <div className={styles.centered}>Некорректный адрес.</div>
      </PageFrame>
    );
  }

  if (attemptsQuery.isLoading) {
    return (
      <PageFrame>
        <div className={styles.centered}><Spinner /></div>
      </PageFrame>
    );
  }

  if (attemptsQuery.isError || !attemptsQuery.data) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <Button type="button" onClick={() => void attemptsQuery.refetch()}>Обновить</Button>
        </div>
      </PageFrame>
    );
  }

  const rows = attemptsQuery.data.filter((item) => item.homework_slug === homeworkSlug);

  return (
    <PageFrame>
      <div className={styles.wrap}>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link to={`/app/courses/${courseSlug}/${lessonSlug}`}>Урок</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>Проверка ДЗ</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>

        <div className={styles.card}>
          <h2 className={styles.title}>Попытки по заданию</h2>
          {rows.length === 0 ? (
            <p className={styles.empty}>По этому ДЗ пока нет попыток.</p>
          ) : (
            <ul className={styles.list}>
              {rows.map((row) => (
                <li key={row.attempt_id} className={styles.item}>
                  <div className={styles.meta}>
                    <span>Попытка: {row.attempt_id}</span>
                    <span>Статус: {row.status}</span>
                    <span>Отправлено: {formatDate(row.send_at)}</span>
                  </div>
                  <Link
                    className={styles.link}
                    to={`/app/courses/${courseSlug}/${lessonSlug}/homework/${homeworkSlug}/review/${row.attempt_id}`}
                  >
                    {row.status === 'submitted' ? 'Проверить' : 'Открыть'}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </PageFrame>
  );
}
