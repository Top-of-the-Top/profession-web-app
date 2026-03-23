import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Spinner, PageTransition } from '../../../shared/ui';
import { courseApi, type Course } from '../../../shared/api/courseApi';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifyWarning,
} from '../../../shared/lib/sileo/notify';
import styles from './CourseDetailPage.module.css';

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

function notifyCourseDetailError(err: unknown) {
  if (isAuthLike(err)) {
    notifyWarning({
      title: 'нужна авторизация',
      description: 'Войдите, чтобы просмотреть страницу курса.',
    });
    return;
  }
  const parsed = parseApiError(err);
  if (parsed) {
    const m = messageForApiFailure('courseDetail', parsed.status, parsed.body);
    notifyError({ title: m.title, description: m.description });
    return;
  }
  const fb = messageForApiFailure('courseDetail', 0, {});
  notifyError({ title: fb.title, description: fb.description });
}

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) {
      setError('Курс не указан в адресе');
      setLoading(false);
      notifyWarning({
        title: 'неверная ссылка',
        description: 'Откройте курс из каталога.',
      });
      return;
    }

    const fetchCourse = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await courseApi.getCourseBySlug(slug);
        setCourse(data.course);
      } catch (err) {
        notifyCourseDetailError(err);
        setError(
          isAuthLike(err)
            ? 'Нужна авторизация'
            : 'Не удалось загрузить курс',
        );
      } finally {
        setLoading(false);
      }
    };

    void fetchCourse();
  }, [slug]);

  if (loading) {
    return <div className={styles.container}><Spinner full /></div>;
  }

  if (error || !course) {
    return (
      <div className={styles.container}>
        <p>{error ?? 'Курс недоступен'}</p>
        <Button
          style={{ marginTop: 16 }}
          variant="secondary"
          onClick={() => navigate('/app/store')}
        >
          В каталог
        </Button>
      </div>
    );
  }

  return (
    <PageTransition className={styles.container}>
      <h1 className={styles.pageTitle}>{course.title}</h1>

      <div className={styles.contentWrapper}>
        <div className={styles.mainContent}>
          <div className={styles.imageSection}>
            <img
              src={course.image_url}
              alt={course.title}
              className={styles.courseImage}
            />
          </div>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>О курсе</h2>
            <p className={styles.text}>{course.description}</p>
          </section>
        </div>

        <aside className={styles.sidebar}>
          <div className={styles.priceCard}>
            <div className={styles.priceHeader}>
              <span>Сумма</span>
              <span className={styles.price}>{course.price} ₽</span>
            </div>
            <Button className={styles.selectButton}>Выбрать</Button>
          </div>
        </aside>
      </div>
    </PageTransition>
  );
}
