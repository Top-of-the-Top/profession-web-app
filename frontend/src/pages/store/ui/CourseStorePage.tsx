// CourseStorePage.tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { Button } from '../../../shared/ui';
import { courseApi, type CourseDTO, } from '../../../shared/api/courseApi';
import styles from './CourseStorePage.module.css';

interface CourseCardProps {
  course: CourseDTO;
  onClick: () => void;
}

const CourseCard = ({ course, onClick }: CourseCardProps) => {
  const formattedPrice = new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(course.price);

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
          onClick={(e) => {
            e.stopPropagation();
            console.log('Выбран курс:', course.title);
          }}
        >
          Выбрать
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

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await courseApi.getCourses();
        
        console.log('Courses data:', data);
        
        setCourses(data.data)
      } catch (err) {
        console.error('Ошибка загрузки курсов:', err);
        setError('Не удалось загрузить курсы. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  const handleCourseClick = (slug: string) => {
    navigate(`/app/courses/${slug}`);
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
            />
          ))}
        </div>
      )}
    </div>
  );
}