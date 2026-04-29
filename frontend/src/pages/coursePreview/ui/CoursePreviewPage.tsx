import { useParams, useNavigate } from 'react-router-dom';
import { Button, PageFrame, Skeleton } from '@shared/ui';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyCartCourseAdded,
  notifyError,
  notifyWarning,
} from '@shared/lib/sileo/notify';
import { useCourseBySlug } from '@shared/api/queries/courses';
import { useCart } from '@shared/api/queries/cart';
import { useAddToCart } from '@shared/api/mutations/cart';
import styles from './CoursePreviewPage.module.css';

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

export default function CoursePreviewPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const { data: courseData, isLoading, error } = useCourseBySlug(slug);
  const { data: cart, isLoading: cartLoading } = useCart();
  const addToCart = useAddToCart();

  const course = courseData ?? null;
  const inCart = slug
    ? (cart?.courses?.some((c) => c.slug === slug) ?? false)
    : false;

  const handleAddToCart = () => {
    if (!slug || !course || inCart) return;

    addToCart.mutate(slug, {
      onSuccess: () => {
        notifyCartCourseAdded({
          title: 'курс добавлен в корзину',
          description: `«Курс "${course.title}" добавлен в корзину`,
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

  const isInitialLoading = isLoading && !course;

  if (isInitialLoading) {
    return (
      <PageFrame>
        <Skeleton className={styles.skeletonPageTitle} />
        <div className={styles.layout}>
          <div className={styles.mainContent}>
            <div className={styles.imageSection}>
              <Skeleton className={styles.skeletonImage} />
            </div>
            <section className={styles.section}>
              <Skeleton className={styles.skeletonSectionTitle} />
              <Skeleton className={styles.skeletonTextLine} />
              <Skeleton className={styles.skeletonTextLine} />
              <Skeleton className={styles.skeletonTextLineShort} />
            </section>
          </div>
          <aside className={styles.sidebar}>
            <div className={styles.priceCard}>
              <div className={styles.priceHeader}>
                <Skeleton className={styles.skeletonPriceLabel} />
                <Skeleton className={styles.skeletonPriceValue} />
              </div>
              <Skeleton className={styles.skeletonSelectButton} />
            </div>
          </aside>
        </div>
      </PageFrame>
    );
  }

  if (error || !course) {
    return (
      <PageFrame>
        <p>{error ? 'Не удалось загрузить курс' : 'Курс недоступен'}</p>
        <Button
          style={{ marginTop: 16 }}
          variant="secondary"
          onClick={() => navigate('/app/store')}
        >
          В каталог
        </Button>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <h1 className={styles.pageTitle}>{course.title}</h1>

      <div className={styles.layout}>
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
            <Button
              className={styles.selectButton}
              disabled={addToCart.isPending || inCart || cartLoading}
              onClick={handleAddToCart}
            >
              {inCart
                ? 'В корзине'
                : addToCart.isPending
                  ? 'Добавляем...'
                  : 'Выбрать'}
            </Button>
          </div>
        </aside>
      </div>
    </PageFrame>
  );
}
