import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, PageTransition, Spinner } from '../../../shared/ui';
import { courseApi, type PurchasedCourseItem } from '../../../shared/api/courseApi';
import styles from './AppHomePage.module.css';

const PLACEHOLDER_IMG =
  'https://via.placeholder.com/640x400/f0f2f5/64748b?text=%D0%9D%D0%B5%D1%82+%D1%84%D0%BE%D1%82%D0%BE';

function CourseCard({
  item,
  onOpen,
}: {
  item: PurchasedCourseItem;
  onOpen: (slug: string) => void;
}) {
  const { course } = item;
  return (
    <button
      type="button"
      className={styles.card}
      onClick={() => onOpen(course.slug)}
    >
      <div className={styles.cardBody}>
        <h3 className={styles.cardTitle}>{course.title}</h3>
        <p className={styles.cardDescription}>{course.sub_title}</p>
        {!item.is_active ? (
          <span className={styles.expiredBadge}>Доступ истёк</span>
        ) : null}
      </div>
			
      <div className={styles.imageWrap}>
        <img
          src={course.image_url || PLACEHOLDER_IMG}
          alt=""
          className={styles.image}
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLImageElement).src = PLACEHOLDER_IMG;
          }}
        />
      </div>
    </button>
  );
}

export default function AppHomePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<PurchasedCourseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await courseApi.getCoursesForAppHome();
        if (!cancelled) {
          setItems(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error('Ошибка загрузки моих курсов:', err);
        if (!cancelled) {
          setError(
            'Не удалось загрузить курсы. Пожалуйста, попробуйте позже.',
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  const openCourse = (slug: string) => {
    navigate(`/app/courses/${slug}/lessons`);
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.headerRow}>
          <h1 className={styles.title}>Курсы</h1>
        </div>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.headerRow}>
          <h1 className={styles.title}>Курсы</h1>
        </div>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>{error}</p>
          <Button onClick={() => window.location.reload()}>Попробовать снова</Button>
        </div>
      </div>
    );
  }

  return (
    <PageTransition className={styles.page}>
      <div className={styles.headerRow}>
        <h1 className={styles.title}>Курсы</h1>
      </div>

      {items.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyTitle}>Пока нет курсов</p>
          <p className={styles.emptyHint}>
            Загляните в{' '}
            <Link to="/app/store">магазин</Link>, чтобы выбрать обучение.
          </p>
        </div>
      ) : (
        <div className={styles.grid}>
          {items.map((item) => (
            <CourseCard key={item.id} item={item} onOpen={openCourse} />
          ))}
        </div>
      )}
    </PageTransition>
  );
}
