import { Link } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Skeleton,
  PageTransition,
} from '../../shared/ui';
import { parseApiError } from '../../shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifyWarning,
} from '../../shared/lib/sileo/notify';
import { useCart } from '../../shared/api/queries/cart';
import { useRemoveFromCart } from '../../shared/api/mutations/cart';
import { cn } from '../../shared/lib/utils';
import styles from './Cart.module.css';

import { X } from 'lucide-react';

const formatPrice = (value: number) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

function CartSkeleton() {
  return (
    <PageTransition className={styles.cartPage}>
      <h1 className={styles.cartTitle}>Корзина</h1>
      <div className={styles.cartLayout}>
        <div className={styles.cartList}>
          {Array.from({ length: 4 }).map((_, idx) => (
            <div key={idx} className={styles.cartItem}>
              <div className={styles.cartItemInfo}>
                <Skeleton className={styles.skeletonItemTitle} />
                <Skeleton className={styles.skeletonItemSubtitle} />
              </div>
              <div className={styles.cartItemPriceBlock}>
                <Skeleton className={styles.skeletonItemPeriod} />
                <Skeleton className={styles.skeletonItemPrice} />
                <Skeleton className={styles.skeletonItemHint} />
              </div>
            </div>
          ))}
        </div>
        <aside className={styles.cartSummary}>
          <Card className={styles.summaryCard}>
            <CardHeader className={styles.summaryHeader}>
              <Skeleton className={styles.skeletonSummaryTitle} />
              <Skeleton className={styles.skeletonSummaryAmount} />
            </CardHeader>
            <CardContent className={styles.summaryContent}>
              <Skeleton className={styles.skeletonPayButton} />
            </CardContent>
          </Card>
        </aside>
      </div>
    </PageTransition>
  );
}

export default function CartPage() {
  const { data: cart, isLoading: loading, error, refetch } = useCart();
  const removeFromCart = useRemoveFromCart();

  const handleRemove = (slug: string) => {
    removeFromCart.mutate(slug, {
      onError: (err) => {
        if (isAuthLike(err)) {
          notifyWarning({
            title: 'сессия устарела',
            description: 'Войдите снова и повторите действие.',
          });
          return;
        }
        const parsed = parseApiError(err);
        if (parsed) {
          const m = messageForApiFailure('cartRemove', parsed.status, parsed.body);
          notifyError({ title: m.title, description: m.description });
          return;
        }
        const fb = messageForApiFailure('cartRemove', 0, {});
        notifyError({ title: fb.title, description: fb.description });
      },
    });
  };

  if (loading) {
    return <CartSkeleton />;
  }

  if (error) {
    const errMsg = isAuthLike(error)
      ? 'Нужна авторизация'
      : 'Не удалось загрузить корзину';

    return (
      <div className={styles.cartPage}>
        <h1 className={styles.cartTitle}>Корзина</h1>
        <div className={styles.centerBlock}>
          <p>{errMsg}</p>
          <Button
            style={{ marginTop: 16 }}
            variant="secondary"
            onClick={() => void refetch()}
          >
            Повторить
          </Button>
        </div>
      </div>
    );
  }

  const courses = cart?.courses ?? [];

  if (courses.length === 0) {
    return (
      <div className={cn(styles.cartPage, styles.cartPageEmpty)}>
        <div className={styles.emptyState}>
          <img
            src="/cart-empty.svg"
            alt=""
            className={styles.emptyIcon}
            decoding="async"
          />
          <h2 className={styles.emptyHeading}>В корзине пока пусто</h2>
          <p className={styles.emptySubtext}>
            Перейди в{' '}
            <Link to="/app/store" className={styles.emptyStoreLink}>
              магазин
            </Link>
            , чтобы подобрать <br /> подходящий формат обучения
          </p>
        </div>
      </div>
    );
  }

  const total = courses.reduce((sum, course) => sum + course.price, 0);
  const formattedTotal = formatPrice(total);

  return (
    <PageTransition className={styles.cartPage}>
      <h1 className={styles.cartTitle}>Корзина</h1>

      <div className={styles.cartLayout}>
        <div className={styles.cartList}>
          {courses.map((course) => (
            <div key={course.course_id} className={styles.cartItem}>
              <button
                className={styles.cartItemRemove}
                onClick={() => handleRemove(course.slug)}
                title="Удалить из корзины"
                type="button"
              >
                <X />
              </button>

              <div className={styles.cartItemInfo}>
                <h2 className={styles.cartItemTitle}>{course.title}</h2>
                <p className={styles.cartItemSubtitle}>{course.sub_title}</p>
              </div>

              <div className={styles.cartItemPriceBlock}>
                <div className={styles.cartItemPeriod}>1 месяц</div>
                <div className={styles.cartItemPrice}>
                  {formatPrice(course.price)}
                </div>
                <div className={styles.cartItemHint}>Ежемесячная плата</div>
              </div>
            </div>
          ))}
        </div>

        <aside className={styles.cartSummary}>
          <Card className={styles.summaryCard}>
            <CardHeader className={styles.summaryHeader}>
              <CardTitle className={styles.summaryTitle}>Сумма</CardTitle>
              <span className={styles.summaryAmount}>{formattedTotal}</span>
            </CardHeader>
            <CardContent className={styles.summaryContent}>
             
              <Button className={styles.payButton}>Перейти к оплате</Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </PageTransition>
  );
}
