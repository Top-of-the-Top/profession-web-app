import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, PageFrame, Skeleton } from '@shared/ui';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyCartCourseAdded,
  notifyError,
  notifySuccess,
  notifyWarning,
} from '@shared/lib/sileo/notify';
import { useCourseBySlug } from '@shared/api/queries/courses';
import { useCart } from '@shared/api/queries/cart';
import { useAddToCart } from '@shared/api/mutations/cart';
import { useApplyToCourse, useWithdrawApplication } from '@shared/api/mutations/applications';
import { useProfile } from '@shared/api/queries/profile';
import styles from './CoursePreviewPage.module.css';

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

function SpecialCourseBlock({
  courseSlug,
  isEnrolled,
  applicationStatus,
  prefillEmail,
}: {
  courseSlug: string;
  isEnrolled: boolean;
  applicationStatus: 'pending' | 'approved' | 'rejected' | null;
  prefillEmail: string;
}) {
  const [email, setEmail] = useState(prefillEmail);
  const apply = useApplyToCourse(courseSlug);
  const withdraw = useWithdrawApplication(courseSlug);

  if (isEnrolled) {
    return (
      <div className={styles.specialBlock}>
        <Button type="button" className={styles.selectButton} disabled>
          Вы записаны
        </Button>
      </div>
    );
  }

  if (applicationStatus === 'pending') {
    return (
      <div className={styles.specialBlock}>
        <Button
          type="button"
          className={styles.selectButton}
          disabled
        >
          Заявка подана
        </Button>
        <Button
          type="button"
          variant="outline"
          className={styles.selectButton}
          disabled={withdraw.isPending}
          onClick={() => withdraw.mutate()}
        >
          {withdraw.isPending ? 'Отзываем...' : 'Отозвать заявку'}
        </Button>
      </div>
    );
  }

  if (applicationStatus === 'rejected') {
    return (
      <div className={styles.specialBlock}>
        <Button type="button" className={styles.selectButton} disabled>
          Заявка отклонена
        </Button>
      </div>
    );
  }

  if (applicationStatus === 'approved') {
    return (
      <div className={styles.specialBlock}>
        <Button type="button" className={styles.selectButton} disabled>
          Вы записаны
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.specialBlock}>
      <p className={styles.specialLabel}>Запись по заявке</p>
      <input
        className={styles.emailInput}
        type="email"
        placeholder="Ваш email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <Button
        type="button"
        className={styles.selectButton}
        disabled={apply.isPending || !email.trim()}
        onClick={() => {
          apply.mutate(undefined, {
            onSuccess: () => {
              notifySuccess({
                title: 'Заявка отправлена',
                description: 'Преподаватель рассмотрит её в ближайшее время.',
              });
            },
          });
        }}
      >
        {apply.isPending ? 'Отправляем...' : 'Подать заявку'}
      </Button>
    </div>
  );
}

export default function CoursePreviewPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const { data: courseData, isLoading, error } = useCourseBySlug(slug);
  const { data: cart, isLoading: cartLoading } = useCart();
  const { data: profile } = useProfile();
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
              <Skeleton className={styles.skeletonPriceBadge} />
              <div className={styles.priceBlock}>
                <Skeleton className={styles.skeletonPriceLabel} />
                <Skeleton className={styles.skeletonPriceValue} />
              </div>
              <div className={styles.priceDivider} />
              <Skeleton className={styles.skeletonPriceDetail} />
              <Skeleton className={styles.skeletonPriceDetail} />
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

  const isSpecial = course.is_special ?? false;

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
            {isSpecial ? (
              <>
                <div className={styles.sectionTitle}>Курс по записи</div>
                <SpecialCourseBlock
                  courseSlug={slug!}
                  isEnrolled={course.is_enrolled ?? false}
                  applicationStatus={course.application_status ?? null}
                  prefillEmail={profile?.email ?? ''}
                />
              </>
            ) : (
              <>
                <div className={styles.priceBadge}>СТОИМОСТЬ КУРСА</div>
                <div className={styles.priceBlock}>
                  <span className={styles.priceLabel}>Сумма</span>
                  <span className={styles.price}>{course.price.toLocaleString('ru-RU')} ₽</span>
                </div>
                <div className={styles.priceDivider} />
                <div className={styles.priceDetails}>
                  <div className={styles.priceDetailRow}>
                    <span className={styles.priceDetailKey}>Длительность</span>
                    <span className={styles.priceDetailValue}>3 месяца</span>
                  </div>
                  <div className={styles.priceDetailRow}>
                    <span className={styles.priceDetailKey}>Формат</span>
                    <span className={styles.priceDetailValue}>Онлайн</span>
                  </div>
                </div>
                <Button
                  className={styles.selectButton}
                  disabled={addToCart.isPending || inCart || cartLoading || (course.is_enrolled ?? false)}
                  onClick={handleAddToCart}
                >
                  {(course.is_enrolled ?? false)
                    ? 'Вы записаны'
                    : inCart
                      ? 'В корзине'
                      : addToCart.isPending
                        ? 'Добавляем...'
                        : 'Выбрать'}
                </Button>
              </>
            )}
          </div>
        </aside>
      </div>
    </PageFrame>
  );
}
