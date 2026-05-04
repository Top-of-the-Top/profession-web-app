import { Link, useNavigate } from 'react-router-dom';
import { Button, PageFrame, Skeleton } from '@shared/ui';
import type { PurchasedCourseItem } from '@shared/api/courseApi';
import { useCoursesForHome } from '@shared/api/queries/courses';
import styles from './AppHomePage.module.css';

const PLACEHOLDER_IMG =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='640' height='400' viewBox='0 0 640 400'><rect width='100%25' height='100%25' fill='%23f0f2f5'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial,sans-serif' font-size='24' fill='%2364748b'>Нет фото</text></svg>";

function CourseCard({
  item,
  onOpen,
}: {
  item: PurchasedCourseItem;
  onOpen: (slug: string) => void;
}) {
  const course = item.course;
  return (
    <button
      type="button"
      className={styles.card}
      onClick={() => onOpen(course.slug)}
    >
      <div className={styles.cardBody}>
        <h3 className={styles.cardTitle}>{course.title}</h3>
        <p className={styles.cardDescription}>{course.sub_title}</p>
      </div>

      <div className={styles.imageWrap}>
        <img
          src={course.image_url || PLACEHOLDER_IMG}
          alt=""
          className={styles.image}
          loading="lazy"
          onError={(e) => {
            const img = e.target as HTMLImageElement;
            if (img.src !== PLACEHOLDER_IMG) {
              img.src = PLACEHOLDER_IMG;
            }
          }}
        />
      </div>
    </button>
  );
}

function HomeSkeleton() {
  return (
    <>
		<div className={styles.headerRow}>
        <h1 className={styles.title}>Курсы</h1>
      </div>
      <div className={styles.grid}>
        {Array.from({ length: 6 }).map((_, idx) => (
          <div key={idx} className={styles.card}>
            <div className={styles.cardBody}>
              <Skeleton className={styles.skeletonCardTitle} />
              <Skeleton className={styles.skeletonCardDescription} />
              <Skeleton className={styles.skeletonCardDescriptionShort} />
            </div>
            <div className={styles.imageWrap}>
              <Skeleton className={styles.skeletonImage} />
            </div>
          </div>
        ))}
      </div></>
  );
}

export default function AppHomePage() {
  const navigate = useNavigate();
  const { data: items = [], isLoading, error, refetch } = useCoursesForHome();

  const openCourse = (slug: string) => {
    navigate(`/app/courses/${slug}`);
  };

  if (isLoading) {
    return (
      <PageFrame>
        <HomeSkeleton />
      </PageFrame>
    );
  }

  if (error) {
    return (
      <PageFrame>
        <div className={styles.headerRow}>
          <h1 className={styles.title}>Курсы</h1>
        </div>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>
            Не удалось загрузить курсы. Пожалуйста, попробуйте позже.
          </p>
          <Button onClick={() => void refetch()}>Попробовать снова</Button>
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
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
            <CourseCard key={String(item.id)} item={item} onOpen={openCourse} />
          ))}
        </div>
      )}
    </PageFrame>
  );
}
