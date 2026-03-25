import { useEffect, useState } from 'react';
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
import { courseApi, type Course, type Lesson } from '../../../shared/api/courseApi';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifyWarning,
} from '../../../shared/lib/sileo/notify';
import styles from './CourseLessonsPage.module.css';
import {
  USE_MOCK,
  MOCK_COURSE,
  MOCK_LESSONS,
} from './mockCourseLessonsData';

function isAuthLike(err: unknown) {
  const msg = err instanceof Error ? err.message : '';
  return msg === 'AUTH_EXPIRED' || msg.includes('API_ERROR_401');
}

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

function notifyLoadError(err: unknown) {
  if (isAuthLike(err)) {
    notifyWarning({
      title: 'нужна авторизация',
      description: 'Войдите, чтобы открыть уроки курса.',
    });
    return;
  }
  const parsed = parseApiError(err);
  if (parsed) {
    const m = messageForApiFailure('courseDetail', parsed.status, parsed.body);
    notifyError({ title: m.title, description: m.description });
    return;
  }
  const fb = messageForApiFailure('courseDetail', 0, {});
  notifyError({ title: fb.title, description: fb.description });
}

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) {
      setError('Курс не указан в адресе');
      setLoading(false);
      notifyWarning({
        title: 'неверная ссылка',
        description: 'Откройте курс из списка.',
      });
      return;
    }

    if (USE_MOCK) {
      setCourse(MOCK_COURSE);
      setLessons(MOCK_LESSONS);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError(null);
        const [courseRes, lessonsRes] = await Promise.all([
          courseApi.getCourseBySlug(slug),
          courseApi.getLessons(slug),
        ]);
        if (!cancelled) {
          setCourse(courseRes.course);
          setLessons(Array.isArray(lessonsRes) ? lessonsRes : []);
        }
      } catch (err) {
        notifyLoadError(err);
        if (!cancelled) {
          setError(
            isAuthLike(err)
              ? 'Нужна авторизация'
              : 'Не удалось загрузить уроки',
          );
          setCourse(null);
          setLessons([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [slug]);

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
          <p className={styles.errorText}>{error ?? 'Курс недоступен'}</p>
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
