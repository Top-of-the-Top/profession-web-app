import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Spinner,
  PageTransition,
} from '../../shared/ui';
import { cartApi, type CartResponse } from '../../shared/api/cartApi';
import { useCartSummaryStore } from '../../entities/cart/model/cartSummaryStore';
import { parseApiError } from '../../shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifyWarning,
} from '../../shared/lib/sileo/notify';
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

function notifyCartLoadError(err: unknown) {
  if (isAuthLike(err)) {
    notifyWarning({
      title: 'нужна авторизация',
      description: 'Войдите, чтобы открыть корзину.',
    });
    return;
  }
  const parsed = parseApiError(err);
  if (parsed) {
    const m = messageForApiFailure('cartLoad', parsed.status, parsed.body);
    notifyError({ title: m.title, description: m.description });
    return;
  }
  const fb = messageForApiFailure('cartLoad', 0, {});
  notifyError({ title: fb.title, description: fb.description });
}

function notifyCartRemoveError(err: unknown) {
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
}

export default function CartPage() {
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCart = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await cartApi.getCart();
      setCart(data);
      useCartSummaryStore.getState().setHasItems(data.courses.length > 0);
    } catch (err) {
      notifyCartLoadError(err);
      if (isAuthLike(err)) {
        useCartSummaryStore.getState().setHasItems(false);
      }
      setError(
        isAuthLike(err)
          ? 'Нужна авторизация'
          : 'Не удалось загрузить корзину',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCart();
  }, [loadCart]);

  const handleRemove = async (slug: string) => {
    if (!cart) return;

    const prevCourses = cart.courses;
    const updatedCourses = prevCourses.filter((c) => c.slug !== slug);
    setCart({ ...cart, courses: updatedCourses });

    try {
      await cartApi.removeCourse(slug);
      useCartSummaryStore
        .getState()
        .setHasItems(updatedCourses.length > 0);
    } catch (err) {
      setCart({ ...cart, courses: prevCourses });
      notifyCartRemoveError(err);
    }
  };

  if (loading) {
    return (
      <div className={styles.cartPage}>
        <Spinner full />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.cartPage}>
        <h1 className={styles.cartTitle}>Корзина</h1>
        <div className={styles.centerBlock}>
          <p>{error}</p>
          <Button
            style={{ marginTop: 16 }}
            variant="secondary"
            onClick={() => void loadCart()}
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
