import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { Button, Spinner, PageTransition } from '../../../shared/ui';
import type { CourseDTO } from '../../../shared/api/courseApi';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyCartCourseAdded,
  notifyError,
  notifyWarning,
} from '../../../shared/lib/sileo/notify';
import { useCourses } from '../../../shared/api/queries/courses';
import { useCart } from '../../../shared/api/queries/cart';
import { useAddToCart } from '../../../shared/api/mutations/cart';
import styles from './CourseStorePage.module.css';

interface CourseCardProps {
  course: CourseDTO;
  onClick: () => void;
  onAddToCart: () => void;
  disabled?: boolean;
  inCart?: boolean;
}

const CourseCard = ({ course, onClick, onAddToCart, disabled, inCart }: CourseCardProps) => {
  return (
    <div className={styles.courseCard}>
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
            (e.target as HTMLImageElement).src = 'https://via.placeholder.com/400x300?text=No+Image';
          }}
        />
      </div>

      <div className={styles.courseActions}>
        <Button 
          variant="ghost" 
          className={styles.detailsButton}
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
          {inCart ? 'В корзине' : 'В коризну'}
        </Button>
      </div>
    </div>
  );
};

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
    navigate(`/app/courses/${slug}`);
  };

  const handleAddToCart = (slug: string, title: string) => {
    addToCart.mutate(slug, {
      onSuccess: () => {
        notifyCartCourseAdded({
          title: 'курс добавлен в корзину',
          description: `«${title}» — можно перейти к оформлению.`,
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
      <div className={styles.catalog}>
        <h2 className={styles.catalogTitle}>Каталог курсов</h2>
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.catalog}>
        <h2 className={styles.catalogTitle}>Каталог курсов</h2>
        <div className={styles.errorState}>
          <p className={styles.errorMessage}>
            Не удалось загрузить курсы. Пожалуйста, попробуйте позже.
          </p>
          <Button onClick={() => void refetch()}>
            Попробовать снова
          </Button>
        </div>
      </div>
    );
  }

  return (
    <PageTransition className={styles.catalog}>
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
              disabled={addToCart.isPending && addToCart.variables === course.slug}
              inCart={inCartSlugs.has(course.slug)}
            />
          ))}
        </div>
      )}
    </PageTransition>
  );
}
