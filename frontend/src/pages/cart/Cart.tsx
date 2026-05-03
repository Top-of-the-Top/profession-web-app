import { useId, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Button,
  Modal,
  PageFrame,
  Skeleton,
  Spinner,
} from '@shared/ui';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifyWarning,
} from '@shared/lib/sileo/notify';
import { useCart } from '@shared/api/queries/cart';
import { usePayCart, useRemoveFromCart } from '@shared/api/mutations/cart';
import styles from './Cart.module.css';

import { X } from 'lucide-react';

const formatPrice = (value: number) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

function formatCourseCountLabel(count: number): string {
  const m100 = count % 100;
  if (m100 >= 11 && m100 <= 14) {
    return `${count} курсов`;
  }
  const m = count % 10;
  if (m === 1) return `${count} курс`;
  if (m >= 2 && m <= 4) return `${count} курса`;
  return `${count} курсов`;
}

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

function CartSkeleton() {
  return (
    <>
      <h1 className={styles.cartTitle}>Корзина</h1>
      <div className={styles.layout}>
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
          <div className={styles.summaryCard}>
            <Skeleton className={styles.skeletonSummaryBadge} />
            <Skeleton className={styles.skeletonSummaryTitle} />
            <Skeleton className={styles.skeletonSummaryTitle} />
            <div className={styles.summaryDivider} />
            <Skeleton className={styles.skeletonSummaryAmount} />
            <div className={styles.summaryDivider} />
            <Skeleton className={styles.skeletonSummaryAmount} />
            <Skeleton className={styles.skeletonPayButton} />
          </div>
        </aside>
      </div>
    </>
  );
}

export default function CartPage() {
  const navigate = useNavigate();
  const { data: cart, isLoading: loading, error, refetch } = useCart();
  const removeFromCart = useRemoveFromCart();
  const payCart = usePayCart();
  const [payDialogOpen, setPayDialogOpen] = useState(false);
  const payModalTitleId = useId();
  const payModalDescId = useId();

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
          const m = messageForApiFailure(
            'cartRemove',
            parsed.status,
            parsed.body
          );
          notifyError({ title: m.title, description: m.description });
          return;
        }
        const fb = messageForApiFailure('cartRemove', 0, {});
        notifyError({ title: fb.title, description: fb.description });
      },
    });
  };

  if (loading) {
    return (
      <PageFrame>
        <CartSkeleton />
      </PageFrame>
    );
  }

  if (error) {
    const errMsg = isAuthLike(error)
      ? 'Нужна авторизация'
      : 'Не удалось загрузить корзину';

    return (
      <PageFrame>
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
      </PageFrame>
    );
  }

  const courses = cart?.courses ?? [];

  if (courses.length === 0) {
    return (
      <PageFrame className={styles.emptyLayout}>
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
      </PageFrame>
    );
  }

  const total = courses.reduce((sum, course) => sum + course.price, 0);
  const formattedTotal = formatPrice(total);

  return (
    <PageFrame>
      <h1 className={styles.cartTitle}>Корзина</h1>

      <div className={styles.layout}>
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
          <div className={styles.summaryCard}>
            <div className={styles.summaryBadge}>ВАШ ЗАКАЗ</div>

            <div className={styles.summaryRows}>
              {courses.map((course) => (
                <div key={course.course_id} className={styles.summaryRow}>
                  <span className={styles.summaryRowTitle}>{course.title}</span>
                  <span className={styles.summaryRowPrice}>{formatPrice(course.price)}</span>
                </div>
              ))}
            </div>

            <div className={styles.summaryDivider} />

            <div className={styles.summaryTotalRow}>
              <span className={styles.summaryTotalLabel}>Сумма заказа</span>
              <span className={styles.summaryTotalValue}>{formattedTotal}</span>
            </div>

            <div className={styles.summaryDivider} />

            <div className={styles.summaryPayRow}>
              <span className={styles.summaryPayLabel}>К оплате</span>
              <div className={styles.summaryPayRight}>
                <span className={styles.summaryPayAmount}>{formattedTotal}</span>
                <span className={styles.summaryPayHint}>ежемесячный платёж</span>
              </div>
            </div>

            <Button
              type="button"
              className={styles.payButton}
              disabled={payCart.isPending}
              onClick={() => setPayDialogOpen(true)}
            >
              {payCart.isPending ? 'Оформление…' : 'Перейти к оплате'}
            </Button>
          </div>
        </aside>
      </div>

      <Modal
        open={payDialogOpen}
        onClose={() => {
          if (!payCart.isPending) setPayDialogOpen(false);
        }}
        backdropClassName={styles.payDialogOverlay}
        panelClassName={styles.payDialog}
        closeOnBackdrop={!payCart.isPending}
        labelledBy={payModalTitleId}
        describedBy={payModalDescId}
      >
        <div className={styles.payDialogRoot}>
          {payCart.isPending ? (
            <div className={styles.payDialogLoadingLayer}>
              <Spinner />
              <span className={styles.payDialogLoadingText}>
                Обрабатываем оплату…
              </span>
            </div>
          ) : null}

          <h2 id={payModalTitleId} className={styles.payVisuallyHidden}>
            Оплата заказа через T‑Pay
          </h2>
          <p id={payModalDescId} className={styles.payVisuallyHidden}>
            Сумма {formattedTotal}, позиций в заказе: {courses.length}
          </p>

          <header className={styles.payDialogHeader}>
            <button
              type="button"
              className={styles.payDialogClose}
              disabled={payCart.isPending}
              onClick={() => {
                if (!payCart.isPending) setPayDialogOpen(false);
              }}
              aria-label="Закрыть"
            >
              <X aria-hidden />
            </button>
            <div className={styles.payDialogBrand}>
              <span className={styles.payDialogBrandBadge} aria-hidden>
                T
              </span>
              <span className={styles.payDialogBrandPay}>Pay</span>
            </div>
            <span className={styles.payDialogHeaderSpacer} aria-hidden />
          </header>

          <p className={styles.payDialogCashbackHint}>Кэшбэк до 30%</p>

          <div className={styles.payDialogCardStrip}>
            <div className={styles.payDialogCardTop}>
              <span className={styles.payDialogCardName}>Основная карта</span>
              <span className={styles.payDialogCardAmount}>
                {formattedTotal}
              </span>
            </div>
            <div className={styles.payDialogCardDots} aria-hidden>
              <span className={styles.payDialogCardDot} />
              <span
                className={`${styles.payDialogCardDot} ${styles.payDialogCardDotActive}`}
              />
              <span className={styles.payDialogCardDot} />
            </div>
          </div>

          {/* <div className={styles.payDialogMerchant}>
            <div className={styles.payDialogMerchantIcon} aria-hidden>
              P
            </div>
            <div className={styles.payDialogMerchantText}>
              <span className={styles.payDialogMerchantName}>Profession</span>
              <span className={styles.payDialogMerchantMeta}>
                {formatCourseCountLabel(courses.length)} в заказе
              </span>
            </div>
          </div> */}

          <Button
            type="button"
            className={styles.payConfirmButton}
            disabled={payCart.isPending}
            onClick={() =>
              payCart.mutate(undefined, {
                onSuccess: () => {
                  setPayDialogOpen(false);
                  navigate('/app');
                },
              })
            }
          >
            Оплатить {formattedTotal}
          </Button>
        </div>
      </Modal>
    </PageFrame>
  );
}
