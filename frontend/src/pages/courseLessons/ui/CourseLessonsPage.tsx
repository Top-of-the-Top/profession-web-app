import { Link, useNavigate, useParams } from 'react-router-dom';
import { Home } from 'lucide-react';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  PageTransition,
  Spinner,
	Separator
} from '../../../shared/ui';
import type { Lesson } from '../../../shared/api/courseApi';
import { useCourseBySlug, useLessons } from '../../../shared/api/queries/courses';
import styles from './CourseLessonsPage.module.css';
import {
  USE_MOCK,
  MOCK_COURSE,
  MOCK_LESSONS,
} from './mockCourseLessonsData';

function lessonCardDescription(lesson: Lesson): string {
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      dateStyle: 'long',
      timeStyle: 'short',
    }).format(new Date(lesson.date));
  } catch {
      return '';
  }
}

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const courseQuery = useCourseBySlug(USE_MOCK ? undefined : slug);
  const lessonsQuery = useLessons(USE_MOCK ? undefined : slug);

  const course = USE_MOCK ? MOCK_COURSE : (courseQuery.data?.course ?? null);
  const lessons = USE_MOCK ? MOCK_LESSONS : (lessonsQuery.data ?? []);
  const loading = !USE_MOCK && (courseQuery.isLoading || lessonsQuery.isLoading);
  const error = courseQuery.error || lessonsQuery.error;

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className={styles.page}>
        <div className={styles.errorBox}>
          <p className={styles.errorText}>{error ? 'Не удалось загрузить уроки' : 'Курс недоступен'}</p>
          <Button variant="secondary" onClick={() => navigate('/app/home')}>
            К курсам
          </Button>
        </div>
      </div>
    );
  }

  return (
    <PageTransition className={styles.page}>
      <div className={styles.breadcrumbWrap}>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link
                  to="/app/home"
                  className={styles.homeLink}
                  aria-label="Домашняя"
                >
                  <Home size={18} strokeWidth={2} />
                </Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{course.title}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <h1 className={styles.title}>{course.title}</h1>

      {lessons.length === 0 ? (
        <div className={styles.empty}>В этом курсе пока нет уроков.</div>
      ) : (
        <div className={styles.grid}>
          {lessons.map((lesson) => (
            <Link
              key={lesson.lesson_id}
              to={`/app/courses/${slug}/lessons/${lesson.slug}`}
              className={styles.cardLink}
            >
              <article className={styles.card}>
                <h2 className={styles.cardTitle}>{lesson.title}</h2>
                <Separator className={styles.cardSeparator} color='#E2E8F0' />
                <p className={styles.cardDescription}>
                  {lessonCardDescription(lesson)}
                </p>
              </article>
            </Link>
          ))}
        </div>
      )}
    </PageTransition>
  );
}
