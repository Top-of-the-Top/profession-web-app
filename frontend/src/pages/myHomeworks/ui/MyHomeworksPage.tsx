import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
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
import { useMyHomeworks, useCoursesForHome, useCourseHomeBySlug } from '@shared/api/queries/courses';
import type {
  MyHomeworkStudentItem,
  MyHomeworkTeacherAttempt,
} from '@shared/api/courseApi/types';
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
        : styles.badgePending;

  const label =
    status === 'reviewed'
      ? 'Проверено'
      : status === 'submitted'
        ? 'Ожидает проверки'
        : 'Черновик';

  return <span className={`${styles.badge} ${cls}`}>{label}</span>;
}

// ─── Student ──────────────────────────────────────────────────────────────────

function StudentTable({
  items,
  courseSlug,
  lessonSlug,
}: {
  items: MyHomeworkStudentItem[];
  courseSlug: string;
  lessonSlug: string | undefined;
}) {
  if (items.length === 0) {
    return <div className={styles.empty}>Нет заданий</div>;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Домашнее задание</th>
          <th>Баллы</th>
          <th>Дедлайн</th>
          <th>Статус</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.attempt_id}>
            <td className={styles.hwTitle}>{item.homework_title}</td>
            <td className={styles.scoreText}>
              {item.grade !== null && item.max_points !== null
                ? `${item.grade} / ${item.max_points}`
                : item.max_points !== null
                  ? `— / ${item.max_points}`
                  : '—'}
            </td>
            <td className={styles.dateText}>{formatDate(item.deadline)}</td>
            <td>
              <StatusBadge status={item.status} />
            </td>
            <td>
              {lessonSlug ? (
                <Link
                  className={styles.linkCell}
                  to={`/app/courses/${courseSlug}/${lessonSlug}/homework/${item.homework_slug}`}
                >
                  Открыть <ChevronRight size={14} />
                </Link>
              ) : (
                <span className={styles.dateText}>{item.lesson_title}</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function StudentView({
  items,
  courseSlug,
  lessonSlug,
}: {
  items: MyHomeworkStudentItem[];
  courseSlug: string;
  lessonSlug: string | undefined;
}) {
  const todo = useMemo(() => items.filter((i) => i.status === 'draft'), [items]);
  const pending = useMemo(() => items.filter((i) => i.status === 'submitted'), [items]);
  const reviewed = useMemo(() => items.filter((i) => i.status === 'reviewed'), [items]);

  return (
    <div className={styles.tabsWrap}>
      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">Все ({items.length})</TabsTrigger>
          <TabsTrigger value="todo">Черновики ({todo.length})</TabsTrigger>
          <TabsTrigger value="pending">Ожидает проверки ({pending.length})</TabsTrigger>
          <TabsTrigger value="reviewed">Проверено ({reviewed.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="all">
          <div className={styles.card}>
            <StudentTable items={items} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
        <TabsContent value="todo">
          <div className={styles.card}>
            <StudentTable items={todo} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
        <TabsContent value="pending">
          <div className={styles.card}>
            <StudentTable items={pending} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
        <TabsContent value="reviewed">
          <div className={styles.card}>
            <StudentTable items={reviewed} courseSlug={courseSlug} lessonSlug={lessonSlug} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Teacher ──────────────────────────────────────────────────────────────────

function TeacherTable({
  items,
  courseSlug,
  lessonSlug,
}: {
  items: MyHomeworkTeacherAttempt[];
  courseSlug: string;
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
          <th>Задание</th>
          <th>Баллы</th>
          <th>Статус</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.attempt_id}>
            <td className={styles.studentName}>
              {item.student.first_name} {item.student.last_name}
            </td>
            <td className={styles.hwTitle}>{item.homework_title}</td>
            <td className={styles.scoreText}>
              {item.grade !== null && item.max_points !== null
                ? `${item.grade} / ${item.max_points}`
                : item.max_points !== null
                  ? `— / ${item.max_points}`
                  : '—'}
            </td>
            <td>
              <StatusBadge status={item.status} />
            </td>
            <td>
              {lessonSlug ? (
                <Link
                  className={styles.linkCell}
                  to={`/app/courses/${courseSlug}/${lessonSlug}/homework/${item.homework_slug}/review/${item.attempt_id}`}
                >
                  {item.status === 'submitted' ? 'Проверить' : 'Открыть'}{' '}
                  <ChevronRight size={14} />
                </Link>
              ) : (
                <span className={styles.dateText}>—</span>
              )}
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
  courseSlug: string;
  lessonSlug: string | undefined;
}) {
  const waiting = useMemo(() => items.filter((i) => i.status === 'submitted'), [items]);
  const done = useMemo(() => items.filter((i) => i.status === 'reviewed'), [items]);

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

  const courseSlug = searchParams.get('course_slug') ?? undefined;
  const lessonSlug = searchParams.get('lesson_slug') ?? undefined;

  const coursesQuery = useCoursesForHome();
  const courseHomeQuery = useCourseHomeBySlug(courseSlug);
  const homeworksQuery = useMyHomeworks(courseSlug, lessonSlug);

  const courses = coursesQuery.data ?? [];

  const availableLessons = useMemo<Array<{ slug: string; title: string }>>(() => {
    if (!courseHomeQuery.data) return [];
    return courseHomeQuery.data.content.flatMap((section) =>
      section.lessons.map((l) => ({ slug: l.slug, title: l.title })),
    );
  }, [courseHomeQuery.data]);

  function setFilter(key: 'course_slug' | 'lesson_slug', value: string | undefined) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      if (key === 'course_slug') next.delete('lesson_slug');
      return next;
    });
  }

  function renderContent() {
    if (!courseSlug) {
      return (
        <div className={styles.centered} style={{ color: 'var(--muted-foreground)', fontSize: '0.875rem' }}>
          Выберите курс для просмотра заданий
        </div>
      );
    }
    if (homeworksQuery.isLoading) {
      return <div className={styles.centered}><Spinner /></div>;
    }
    if (homeworksQuery.isError || !homeworksQuery.data) {
      return (
        <div className={styles.centered} style={{ color: 'var(--destructive)' }}>
          Не удалось загрузить данные
        </div>
      );
    }
    if ('my_attempts' in homeworksQuery.data) {
      return (
        <StudentView
          items={homeworksQuery.data.my_attempts.items}
          courseSlug={courseSlug}
          lessonSlug={lessonSlug}
        />
      );
    }
    return (
      <TeacherView
        items={homeworksQuery.data.student_attempts.items}
        courseSlug={courseSlug}
        lessonSlug={lessonSlug}
      />
    );
  }

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
              value={courseSlug ?? '__all__'}
              onValueChange={(val) => setFilter('course_slug', val === '__all__' ? undefined : val)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите курс" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Все курсы</SelectItem>
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
                  value={lessonSlug ?? '__all__'}
                  onValueChange={(val) => setFilter('lesson_slug', val === '__all__' ? undefined : val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Все уроки" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">Все уроки</SelectItem>
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

        {renderContent()}
      </div>
    </PageFrame>
  );
}
