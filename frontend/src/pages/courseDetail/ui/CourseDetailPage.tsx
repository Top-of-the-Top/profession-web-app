'use client';

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../../../shared/ui';
import { courseApi, type Course } from '../../../shared/api/courseApi';
import styles from './CourseDetailPage.module.css';

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) {
      setError('Курс не найден');
      setLoading(false);
      return;
    }

    const fetchCourse = async () => {
      try {
        setLoading(true);
        const data = await courseApi.getCourseBySlug(slug);
        setCourse(data.course);
      } catch (err) {
        setError('Не удалось загрузить курс');
      } finally {
        setLoading(false);
      }
    };

    fetchCourse();
  }, [slug]);

  if (loading) return <div className={styles.container}>Загрузка...</div>;
  if (error || !course) return <div className={styles.container}>Ошибка: {error}</div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>{course.title}</h1>

      <div className={styles.contentWrapper}>
        <div className={styles.mainContent}>
          {/* Изображение курса */}
          <div className={styles.imageSection}>
            <img 
              src={course.image_url} 
              alt={course.title}
              className={styles.courseImage}
            />
          </div>

          {/* О курсе */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>О курсе</h2>
            <p className={styles.text}>{course.sub_title}</p>
          </section>
        </div>

        {/* Боковая панель с ценой */}
        <aside className={styles.sidebar}>
          <div className={styles.priceCard}>
            <div className={styles.priceHeader}>
              <span>Сумма</span>
              <span className={styles.price}>{course.price} ₽</span>
            </div>
            <Button className={styles.selectButton}>Выбрать</Button>
          </div>
        </aside>
      </div>
    </div>
  );
}