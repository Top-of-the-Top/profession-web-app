// CourseStorePage.tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import { Button } from '../../../shared/ui';
import { courseApi, type CourseDTO } from '../../../shared/api/courseApi';
import { cartApi } from '../../../shared/api/cartApi';
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
          {inCart ? 'В корзине' : 'Выбрать'}
        </Button>
      </div>
    </div>
  );
};

export default function CourseStorePage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<CourseDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addingSlug, setAddingSlug] = useState<string | null>(null);
  const [inCartSlugs, setInCartSlugs] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [coursesResponse, cartResponse] = await Promise.all([
          courseApi.getCourses(),
          cartApi.getCart().catch((err: unknown) => {
            const message = (err as Error)?.message ?? '';

            // Если не авторизованы / токен протух — просто считаем, что корзина пустая
            if (
              message === 'AUTH_EXPIRED' ||
              message.includes('API_ERROR_401')
            ) {
              return null;
            }

            throw err;
          }),
        ]);

        setCourses(coursesResponse.data);

        if (cartResponse && Array.isArray(cartResponse.courses)) {
          setInCartSlugs(
            new Set(cartResponse.courses.map((course) => course.slug)),
          );
        } else {
          setInCartSlugs(new Set());
        }
      } catch (err) {
        console.error('Ошибка загрузки курсов:', err);
        setError('Не удалось загрузить курсы. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleCourseClick = (slug: string) => {
    navigate(`/app/courses/${slug}`);
  };

  const handleAddToCart = async (slug: string, title: string) => {
    setAddingSlug(slug);
    try {
      await cartApi.addCourse(slug);
      toast.success(`Курс «${title}» добавлен в корзину`);

      setInCartSlugs((prev) => {
        const next = new Set(prev);
        next.add(slug);
        return next;
      });
    } catch (err: any) {
      const message: string = err?.message ?? '';

      if (message === 'AUTH_EXPIRED' || message.includes('API_ERROR_401')) {
        toast.error('Авторизуйтесь, чтобы добавить курс в корзину');
      } else if (message.includes('API_ERROR_400')) {
        toast.error('Курс уже в корзине');
      } else {
        toast.error('Не удалось добавить курс в корзину');
      }
    } finally {
      setAddingSlug(null);
    }
  };

  if (loading) {
    return (
      <div className={styles.catalog}>
        <h2 className={styles.catalogTitle}>Каталог курсов</h2>
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
          <p>Загрузка курсов...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.catalog}>
        <h2 className={styles.catalogTitle}>Каталог курсов</h2>
        <div className={styles.errorState}>
          <p className={styles.errorMessage}>{error}</p>
          <Button onClick={() => window.location.reload()}>
            Попробовать снова
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      <Toaster position="top-right" />
      <div className={styles.catalog}>
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
                disabled={addingSlug === course.slug}
                inCart={inCartSlugs.has(course.slug)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}