import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { Button, PageFrame, Skeleton } from '@shared/ui';
import type { CourseDTO } from '@shared/api/courseApi';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyCartCourseAdded,
  notifyError,
  notifyWarning,
} from '@shared/lib/sileo/notify';
import { useCourses } from '@shared/api/queries/courses';
import { useCart } from '@shared/api/queries/cart';
import { useAddToCart } from '@shared/api/mutations/cart';
import { preloadCourseDetailsRoutes } from '@router/lazyPages';
import styles from './CourseStorePage.module.css';

const FALLBACK_IMAGE =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'><rect width='100%25' height='100%25' fill='%23f1f5f9'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial,sans-serif' font-size='18' fill='%2364748b'>Нет фото</text></svg>";

interface CourseCardProps {
  course: CourseDTO;
  onClick: () => void;
  onAddToCart: () => void;
  onPrefetch: () => void;
  disabled?: boolean;
  inCart?: boolean;
  isAdding?: boolean;
}

const CourseCard = ({
  course,
  onClick,
  onAddToCart,
  onPrefetch,
  disabled,
  inCart,
  isAdding,
}: CourseCardProps) => {
  return (
    <div
      className={styles.courseCard}
      onPointerEnter={onPrefetch}
      onFocus={onPrefetch}
    >
      <div className={styles.courseHeader}>
        <h3 className={styles.courseTitle}>{course.title}</h3>
        <p className={styles.courseDescription}>{course.sub_title}</p>
      </div>

      <div className={styles.courseImageWrapper}>
        <img
          src={course.image_url}
          alt={course.title}
          className={styles.courseImage}
          loading="lazy"
          onError={(e) => {
            const img = e.target as HTMLImageElement;
            if (img.src !== FALLBACK_IMAGE) {
              img.src = FALLBACK_IMAGE;
            }
          }}
        />
      </div>

      <div className={styles.courseActions}>
        <Button 
          variant="ghost" 
          className={styles.detailsButton}
          onPointerEnter={onPrefetch}
          onFocus={onPrefetch}
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
        >
          <div className={styles.iconWrapper}>
            <ArrowUpRight className={styles.arrowIcon} size={25} />
          </div>
          Подробнее
        </Button>

        <Button
          className={styles.selectButton}
          disabled={disabled || inCart}
          onClick={(e) => {
            e.stopPropagation();
            onAddToCart();
          }}
        >
          {inCart ? 'В корзине' : isAdding ? 'Добавляем...' : 'В корзину'}
        </Button>
      </div>
    </div>
  );
};

const StoreSkeleton = () => (
  <>
	<h2 className={styles.catalogTitle}>Каталог курсов</h2>
    <div className={styles.coursesGrid}>
      {Array.from({ length: 6 }).map((_, idx) => (
        <div key={idx} className={styles.courseCard}>
          <div className={styles.courseHeader}>
            <Skeleton className={styles.skeletonTitle} />
            <Skeleton className={styles.skeletonSubtitle} />
          </div>
          <div className={styles.courseImageWrapper}>
            <Skeleton className={styles.skeletonImage} />
          </div>
          <div className={styles.courseActions}>
            <Skeleton className={styles.skeletonDetailsButton} />
            <Skeleton className={styles.skeletonSelectButton} />
          </div>
        </div>
      ))}
    </div></>
);

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

export default function CourseStorePage() {
  const navigate = useNavigate();

  const { data: coursesData, isLoading, error, refetch } = useCourses();
  const { data: cart } = useCart();
  const addToCart = useAddToCart();

  const courses = coursesData?.data ?? [];
  const inCartSlugs = new Set(cart?.courses?.map((c) => c.slug) ?? []);

  const handleCourseClick = (slug: string) => {
    preloadCourseDetailsRoutes();
    navigate(`/app/store/${slug}`);
  };

  const handleAddToCart = (slug: string, title: string) => {
    addToCart.mutate(slug, {
      onSuccess: () => {
        notifyCartCourseAdded({
          title: 'курс добавлен в корзину',
          description: `«Курс "${title}" добавлен в вашу корзину`,
        });
      },
      onError: (err: unknown) => {
        if (isAuthLike(err)) {
          notifyWarning({
            title: 'нужна авторизация',
            description: 'Войдите в аккаунт, чтобы добавить курс в корзину.',
          });
          return;
        }
        const parsed = parseApiError(err);
        if (parsed) {
          const m = messageForApiFailure('cartAdd', parsed.status, parsed.body);
          notifyError({ title: m.title, description: m.description });
          return;
        }
        const fb = messageForApiFailure('cartAdd', 0, {});
        notifyError({ title: fb.title, description: fb.description });
      },
    });
  };

  if (isLoading) {
    return (
      <PageFrame>
        <StoreSkeleton />
      </PageFrame>
    );
  }

  if (error) {
    return (
      <PageFrame>
        <h2 className={styles.catalogTitle}>Каталог курсов</h2>
        <div className={styles.errorState}>
          <p className={styles.errorMessage}>
            Не удалось загрузить курсы. Пожалуйста, попробуйте позже.
          </p>
          <Button onClick={() => void refetch()}>
            Попробовать снова
          </Button>
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <h2 className={styles.catalogTitle}>Каталог курсов</h2>

      {courses.length === 0 ? (
        <div className={styles.emptyState}>
          <p>Курсы не найдены</p>
        </div>
      ) : (
        <div className={styles.coursesGrid}>
          {courses.map((course) => (
            <CourseCard
              key={course.course_id}
              course={course}
              onClick={() => handleCourseClick(course.slug)}
              onAddToCart={() => handleAddToCart(course.slug, course.title)}
              onPrefetch={preloadCourseDetailsRoutes}
              disabled={addToCart.isPending && addToCart.variables === course.slug}
              isAdding={addToCart.isPending && addToCart.variables === course.slug}
              inCart={inCartSlugs.has(course.slug)}
            />
          ))}
        </div>
      )}
    </PageFrame>
  );
}
