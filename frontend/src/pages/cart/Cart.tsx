import { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
} from '../../shared/ui';
import { cartApi, type CartResponse } from '../../shared/api/cartApi';
import styles from './Cart.module.css';

import { X } from 'lucide-react'

const formatPrice = (value: number) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

export default function CartPage() {
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCart = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await cartApi.getCart();
        setCart(data);
      } catch (err: any) {
        if (err?.message === 'AUTH_EXPIRED') {
          setError('Сессия истекла, пожалуйста, войдите снова.');
        } else {
          setError('Не удалось загрузить корзину. Попробуйте позже.');
        }
      } finally {
        setLoading(false);
      }
    };

    void fetchCart();
  }, []);

  const handleRemove = async (slug: string) => {
    if (!cart) return;

    // Оптимистично обновляем
    const prevCourses = cart.courses;
    const updatedCourses = prevCourses.filter(c => c.slug !== slug);
    setCart({ ...cart, courses: updatedCourses });

    try {
      await cartApi.removeCourse(slug); // Должен вызвать /api/carts/remove/{slug}
    } catch (err) {
      // В случае ошибки возвращаем обратно
      setCart({ ...cart, courses: prevCourses });
      console.error('Ошибка при удалении курса', err);
    }
  };

  if (loading) {
    return (
      <div className={styles.cartPage}>
        <h1 className={styles.cartTitle}>Корзина</h1>
        <div className={styles.centerBlock}>Загрузка корзины...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.cartPage}>
        <h1 className={styles.cartTitle}>Корзина</h1>
        <div className={styles.centerBlock}>{error}</div>
      </div>
    );
  }

  const courses = cart?.courses ?? [];

  if (courses.length === 0) {
    return (
      <div className={styles.cartPage}>
        <h1 className={styles.cartTitle}>Корзина</h1>
        <Card className={styles.emptyCard}>
          <CardContent className={styles.emptyContent}>
            В вашей корзине пока нет курсов.
          </CardContent>
        </Card>
      </div>
    );
  }

  const total = courses.reduce((sum, course) => sum + course.price, 0);
  const formattedTotal = formatPrice(total);

  return (
    <div className={styles.cartPage}>
      <h1 className={styles.cartTitle}>Корзина</h1>

      <div className={styles.cartLayout}>
        <div className={styles.cartList}>
          {courses.map((course) => (
            <div key={course.course_id} className={styles.cartItem}>
              <button
                className={styles.cartItemRemove}
                onClick={() => handleRemove(course.slug)}
                title="Удалить из корзины"
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
              <CardTitle className={styles.summaryTitle}>К оплате</CardTitle>
              <span className={styles.summaryAmount}>{formattedTotal}</span>
            </CardHeader>
            <CardContent className={styles.summaryContent}>
              <div className={styles.summaryRow}>
                <span className={styles.summaryLabel}>Сумма заказа</span>
                <span className={styles.summaryValue}>{formattedTotal}</span>
              </div>
              <Button className={styles.payButton}>Перейти к оплате</Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
