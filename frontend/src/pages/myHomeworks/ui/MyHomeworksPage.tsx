import { useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import {
  PageFrame,
  Spinner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@shared/ui';
import { useMyHomeworks } from '@shared/api/queries/courses';
import { useCoursesForHome } from '@shared/api/queries/courses';
import type {
  MyHomeworkStudentItem,
  MyHomeworkTeacherAttempt,
} from '@shared/api/courseApi/types';
import { useRole } from '@shared/lib/rbac';
import styles from './MyHomeworksPage.module.css';

function formatDate(value: string | null): string {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'reviewed'
      ? styles.badgeReviewed
      : status === 'submitted'
        ? styles.badgeSubmitted
        : status === 'draft'
          ? styles.badgePending
          : styles.badgeNotStarted;

  const label =
    status === 'reviewed'
      ? 'Проверено'
      : status === 'submitted'
        ? 'Ожидает проверки'
        : status === 'draft'
          ? 'Черновик'
          : 'Не начато';

  return <span className={`${styles.badge} ${cls}`}>{label}</span>;
}

// ─── Student table ────────────────────────────────────────────────────────────

function StudentTable({ items }: { items: MyHomeworkStudentItem[] }) {
  if (items.length === 0) {
    return <div className={styles.empty}>Нет заданий</div>;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Домашнее задание</th>
          <th>Баллы</th>
          <th>Дедлайн / Сдано</th>
          <th>Статус</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.homework_id}>
            <td className={styles.hwTitle}>{item.title}</td>
            <td className={styles.scoreText}>
              {item.score !== null && item.max_points !== null
                ? `${item.score} / ${item.max_points}`
                : item.max_points !== null
                  ? `— / ${item.max_points}`
                  : '—'}
            </td>
            <td>
              <div className={styles.dateText}>
                {item.send_at ? formatDate(item.send_at) : formatDate(item.deadline)}
              </div>
            </td>
            <td>
              <StatusBadge status={item.status} />
            </td>
            <td>
              {item.attempt_id ? (
                <Link
                  className={styles.linkCell}
                  to={`/app/courses/${item.course_slug}/${item.lesson_slug}/homework/${item.homework_slug}`}
                >
                  Открыть <ChevronRight size={14} />
                </Link>
              ) : (
                <Link
                  className={styles.linkCell}
                  to={`/app/courses/${item.course_slug}/${item.lesson_slug}/homework/${item.homework_slug}`}
                >
                  Выполнить <ChevronRight size={14} />
                </Link>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StudentView({ items }: { items: MyHomeworkStudentItem[] }) {
  const todo = useMemo(
    () => items.filter((i) => i.status === 'not_started' || i.status === 'draft'),
    [items],
  );
  const pending = useMemo(
    () => items.filter((i) => i.status === 'submitted'),
    [items],
  );
  const reviewed = useMemo(
    () => items.filter((i) => i.status === 'reviewed'),
    [items],
  );

  return (
    <div className={styles.tabsWrap}>
      <Tabs defaultValue="todo">
        <TabsList>
          <TabsTrigger value="todo">К выполнению ({todo.length})</TabsTrigger>
          <TabsTrigger value="pending">Ожидает проверки ({pending.length})</TabsTrigger>
          <TabsTrigger value="reviewed">Проверено ({reviewed.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="todo">
          <div className={styles.card}>
            <StudentTable items={todo} />
          </div>
        </TabsContent>
        <TabsContent value="pending">
          <div className={styles.card}>
            <StudentTable items={pending} />
          </div>
        </TabsContent>
        <TabsContent value="reviewed">
          <div className={styles.card}>
            <StudentTable items={reviewed} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Teacher table ────────────────────────────────────────────────────────────

function TeacherTable({
  items,
  courseSlug,
  lessonSlug,
}: {
  items: MyHomeworkTeacherAttempt[];
  courseSlug: string | undefined;
  lessonSlug: string | undefined;
}) {
  if (items.length === 0) {
    return <div className={styles.empty}>Нет попыток</div>;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Ученик</th>
          <th>Выполнено</th>
          <th>Сдано</th>
          <th>Статус</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.attempt_id}>
            <td className={styles.studentName}>{item.student_name}</td>
            <td className={styles.scoreText}>
              {item.score !== null && item.max_points !== null
                ? `${item.score} / ${item.max_points}`
                : item.max_points !== null
                  ? `— / ${item.max_points}`
                  : '—'}
            </td>
            <td className={styles.dateText}>{formatDate(item.send_at)}</td>
            <td>
              <StatusBadge status={item.status} />
            </td>
            <td>
              <Link
                className={styles.linkCell}
                to={
                  courseSlug && lessonSlug
                    ? `/app/courses/${courseSlug}/${lessonSlug}/homework/${item.homework_slug}/review/${item.attempt_id}`
                    : `/app/courses/${item.course_slug}/${item.lesson_slug}/homework/${item.homework_slug}/review/${item.attempt_id}`
                }
              >
                {item.status === 'submitted' ? 'Проверить' : 'Открыть'}{' '}
                <ChevronRight size={14} />
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TeacherView({
  items,
  courseSlug,
  lessonSlug,
}: {
  items: MyHomeworkTeacherAttempt[];
  courseSlug: string | undefined;
  lessonSlug: string | undefined;
}) {
  const waiting = useMemo(
    () => items.filter((i) => i.status === 'submitted'),
    [items],
  );
  const done = useMemo(
    () => items.filter((i) => i.status === 'reviewed'),
    [items],
  );

  return (
    <div className={styles.tabsWrap}>
      <Tabs defaultValue="waiting">
        <TabsList>
          <TabsTrigger value="waiting">Ждут проверки ({waiting.length})</TabsTrigger>
          <TabsTrigger value="done">Проверены ({done.length})</TabsTrigger>
          <TabsTrigger value="all">Все ({items.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="waiting">
          <div className={styles.card}>
            <TeacherTable items={waiting} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
        <TabsContent value="done">
          <div className={styles.card}>
            <TeacherTable items={done} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
        <TabsContent value="all">
          <div className={styles.card}>
            <TeacherTable items={items} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MyHomeworksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { hasAny } = useRole();
  const isTeacher = hasAny('teacher', 'moderator');

  const courseSlug = searchParams.get('course_slug') ?? undefined;
  const lessonSlug = searchParams.get('lesson_slug') ?? undefined;

  const coursesQuery = useCoursesForHome();
  const homeworksQuery = useMyHomeworks(courseSlug, lessonSlug);

  const courses = coursesQuery.data ?? [];

  // Lessons for the selected course derived from course-home data
  // We don't have lesson list here so we skip lesson sub-filter unless backend returns it
  // The lesson selector is driven by URL only; user picks from available slugs in results

  const availableLessons = useMemo<Array<{ slug: string; title: string }>>(() => {
    if (!homeworksQuery.data) return [];
    if (homeworksQuery.data.role === 'student') {
      const seen = new Map<string, string>();
      for (const item of homeworksQuery.data.items) {
        if (!seen.has(item.lesson_slug)) {
          seen.set(item.lesson_slug, item.lesson_slug);
        }
      }
      return Array.from(seen.entries()).map(([slug]) => ({ slug, title: slug }));
    } else {
      const seen = new Map<string, string>();
      for (const item of homeworksQuery.data.items) {
        if (!seen.has(item.lesson_slug)) {
          seen.set(item.lesson_slug, item.lesson_slug);
        }
      }
      return Array.from(seen.entries()).map(([slug]) => ({ slug, title: slug }));
    }
  }, [homeworksQuery.data]);

  function setFilter(key: 'course_slug' | 'lesson_slug', value: string | undefined) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      // Reset lesson when course changes
      if (key === 'course_slug') {
        next.delete('lesson_slug');
      }
      return next;
    });
  }

  const _ = navigate; // suppress unused warning

  return (
    <PageFrame>
      <div className={styles.wrap}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
          Домашние задания
        </h1>

        <div className={styles.filters}>
          <span className={styles.filterLabel}>Курс:</span>
          <div className={styles.filterSelect}>
            <Select
              value={courseSlug ?? ''}
              onValueChange={(val) => setFilter('course_slug', val || undefined)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все курсы" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Все курсы</SelectItem>
                {courses.map((c) => (
                  <SelectItem key={c.slug} value={c.slug}>
                    {c.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {availableLessons.length > 0 && (
            <>
              <span className={styles.filterLabel}>Урок:</span>
              <div className={styles.filterSelect}>
                <Select
                  value={lessonSlug ?? ''}
                  onValueChange={(val) => setFilter('lesson_slug', val || undefined)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Все уроки" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Все уроки</SelectItem>
                    {availableLessons.map((l) => (
                      <SelectItem key={l.slug} value={l.slug}>
                        {l.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
        </div>

        {homeworksQuery.isLoading ? (
          <div className={styles.centered}>
            <Spinner />
          </div>
        ) : homeworksQuery.isError || !homeworksQuery.data ? (
          <div className={styles.centered} style={{ color: 'var(--destructive)' }}>
            Не удалось загрузить данные
          </div>
        ) : homeworksQuery.data.role === 'student' ? (
          <StudentView items={homeworksQuery.data.items} />
        ) : (
          <TeacherView
            items={homeworksQuery.data.items}
            courseSlug={courseSlug}
            lessonSlug={lessonSlug}
          />
        )}
      </div>
    </PageFrame>
  );
}
