import { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Check, Clock, Search, Home } from 'lucide-react';
import {
  PageFrame,
  Spinner,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@shared/ui';
import { useMyHomeworks, useCoursesForHome, useCourseHomeBySlug } from '@shared/api/queries/courses';
import type { MyHomeworkStudentItem, MyHomeworkTeacherAttempt } from '@shared/api/courseApi/types';
import { cn } from '@shared/lib/utils';
import { homeworkReviewNavigateState } from '@shared/lib/homeworkReviewNavigation';
import styles from './MyHomeworksPage.module.css';

function timeAgo(iso: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins} мин. назад`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ${pluralHours(hours)} назад`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Вчера';
  if (days < 7) return `${days} дня назад`;
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' }).format(new Date(iso));
}

function pluralHours(n: number) {
  if (n % 10 === 1 && n % 100 !== 11) return 'час';
  if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'часа';
  return 'часов';
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'reviewed') {
    return (
      <span className={cn(styles.statusIcon, styles.statusIconReviewed)}>
        <Check size={18} strokeWidth={2.5} />
      </span>
    );
  }
  if (status === 'submitted') {
    return (
      <span className={cn(styles.statusIcon, styles.statusIconSubmitted)}>
        <Clock size={18} strokeWidth={2.5} />
      </span>
    );
  }
  return (
    <span className={cn(styles.statusIcon, styles.statusIconDraft)}>
      <Clock size={18} strokeWidth={2} />
    </span>
  );
}

type Tab = 'waiting' | 'done' | 'all';

// ─── Teacher ──────────────────────────────────────────────────────────────────

function TeacherView({
  items,
  reviewReturnHref,
}: {
  items: MyHomeworkTeacherAttempt[];
  reviewReturnHref: string;
}) {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('waiting');
  const [search, setSearch] = useState('');

  const waiting = useMemo(() => items.filter((i) => i.status === 'submitted'), [items]);
  const done = useMemo(() => items.filter((i) => i.status === 'reviewed'), [items]);
  const allVisible = useMemo(() => items.filter((i) => i.status !== 'draft'), [items]);

  const baseList = tab === 'waiting' ? waiting : tab === 'done' ? done : allVisible;

  const filtered = useMemo(() => {
    if (!search.trim()) return baseList;
    const q = search.toLowerCase();
    return baseList.filter((i) =>
      `${i.student.first_name} ${i.student.last_name}`.toLowerCase().includes(q) ||
      i.student.email.toLowerCase().includes(q) ||
      i.homework_title.toLowerCase().includes(q),
    );
  }, [baseList, search]);

  function tabCount(t: Tab) {
    return t === 'waiting' ? waiting.length : t === 'done' ? done.length : allVisible.length;
  }

  return (
    <>
      <div className={styles.tabsBar}>
        <div className={styles.tabsList}>
          {(['waiting', 'done', 'all'] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              className={cn(styles.tab, tab === t && styles.tabActive)}
              onClick={() => setTab(t)}
            >
              {t === 'waiting' ? 'Ждут проверки' : t === 'done' ? 'Проверены' : 'Все'}
              <span
                className={cn(
                  styles.tabCount,
                  tab === t && t === 'waiting' && styles.tabCountStudentPending,
                  tab === t && t === 'done' && styles.tabCountStudentReviewed,
                )}
              >
                {tabCount(t)}
              </span>
            </button>
          ))}
        </div>

        <label className={styles.searchWrap}>
          <Search size={15} />
          <input
            className={styles.searchInput}
            placeholder="Поиск ученика или задания"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>

      <div className={styles.card}>
        {filtered.length === 0 ? (
          <div className={styles.empty}>Нет попыток</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Ученик</th>
                <th className={styles.colHomework}>Домашнее задание</th>
                <th>Выполнено</th>
                <th>Сдано</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr
                  key={item.attempt_id}
                  onClick={() => {
                    if (!item.course_slug || !item.lesson_slug) return;
                    navigate(
                      `/app/courses/${item.course_slug}/${item.lesson_slug}/homework/${item.homework_slug}/review/${item.attempt_id}`,
                      { state: homeworkReviewNavigateState(reviewReturnHref) },
                    );
                  }}
                  style={{ cursor: item.course_slug && item.lesson_slug ? 'pointer' : 'default' }}
                >
                  <td>
                    <div className={styles.cellStudent}>
                      <span className={styles.studentName}>
                        {item.student.first_name} {item.student.last_name}
                      </span>
                      <span className={styles.studentEmail}>{item.student.email}</span>
                    </div>
                  </td>
                  <td className={styles.colHomework}>
                    <div className={styles.hwTitle}>{item.homework_title}</div>
                  </td>
                  <td>
                    <span className={styles.scoreCell}>
                      {item.grade !== null && item.max_points !== null
                        ? `${item.grade}/${item.max_points}`
                        : item.max_points !== null
                          ? `—/${item.max_points}`
                          : '—'}
                    </span>
                  </td>
                  <td>
                    <span className={styles.dateCell}>
                      {timeAgo(item.send_at)}
                    </span>
                  </td>
                  <td className={styles.statusCell}>
                    <StatusIcon status={item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

// ─── Student ──────────────────────────────────────────────────────────────────

type StudentTab = 'todo' | 'pending' | 'reviewed';

function formatDeadlineFull(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: '—', time: '' };
  const d = new Date(iso);
  const date = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' }).format(d);
  const time = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(d);
  return { date, time };
}

function StudentView({
  items,
}: {
  items: MyHomeworkStudentItem[];
}) {
  const navigate = useNavigate();
  const [tab, setTab] = useState<StudentTab>('todo');
  const [search, setSearch] = useState('');

  const todo = useMemo(() => items.filter((i) => i.status === 'draft'), [items]);
  const pending = useMemo(() => items.filter((i) => i.status === 'submitted'), [items]);
  const reviewed = useMemo(() => items.filter((i) => i.status === 'reviewed'), [items]);

  const baseList = tab === 'todo' ? todo : tab === 'pending' ? pending : reviewed;

  const filtered = useMemo(() => {
    if (!search.trim()) return baseList;
    const q = search.toLowerCase();
    return baseList.filter((i) => i.homework_title.toLowerCase().includes(q));
  }, [baseList, search]);

  const tabDefs: { key: StudentTab; label: string; count: number }[] = [
    { key: 'todo',     label: 'К выполнению',      count: todo.length },
    { key: 'pending',  label: 'Ожидает проверки',   count: pending.length },
    { key: 'reviewed', label: 'Проверено',           count: reviewed.length },
  ];

  return (
    <>
      <div className={styles.tabsBar}>
        <div className={styles.tabsList}>
          {tabDefs.map(({ key, label, count }) => (
            <button
              key={key}
              type="button"
              className={cn(styles.tab, tab === key && styles.tabActive)}
              onClick={() => setTab(key)}
            >
              {label}
              <span
                className={cn(
                  styles.tabCount,
                  tab === key && key === 'todo' && styles.tabCountStudentTodo,
                  tab === key && key === 'pending' && styles.tabCountStudentPending,
                  tab === key && key === 'reviewed' && styles.tabCountStudentReviewed,
                )}
              >
                {count}
              </span>
            </button>
          ))}
        </div>
        <label className={styles.searchWrap}>
          <Search size={15} />
          <input
            className={styles.searchInput}
            placeholder="Поиск домашнего задания"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>

      <div className={styles.card}>
        {filtered.length === 0 ? (
          <div className={styles.empty}>Нет заданий</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Домашнее задание</th>
                <th>Баллы</th>
                <th>{tab === 'pending' ? 'Сдано' : 'Дедлайн'}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const dl = formatDeadlineFull(item.deadline);
                const href = item.course_slug && item.lesson_slug
                  ? `/app/courses/${item.course_slug}/${item.lesson_slug}/homework/${item.homework_slug}`
                  : undefined;
                return (
                  <tr
                    key={item.attempt_id}
                    onClick={() => { if (href) navigate(href); }}
                    style={{ cursor: href ? 'pointer' : 'default' }}
                  >
                    <td>
                      <div className={styles.hwTitle}>{item.homework_title}</div>
                      <div className={styles.hwLesson}>
                        {item.course_title}{item.lesson_title ? ` · ${item.lesson_title}` : ''}
                      </div>
                    </td>
                    <td>
                      <span className={styles.scoreCell}>
                        {item.status === 'draft'
                          ? item.max_points !== null
                            ? `${item.max_points}`
                            : '—'
                          : item.grade !== null
                            ? `${item.grade} / ${item.max_points ?? '?'}`
                            : item.max_points !== null
                              ? `— / ${item.max_points}`
                              : '—'}
                      </span>
                    </td>
                    <td>
                      {item.status === 'submitted' && item.send_at ? (
                        <span className={styles.dateCell}>{timeAgo(item.send_at)}</span>
                      ) : (
                        <>
                          <div className={styles.deadlineDate}>{dl.date}</div>
                          {dl.time && <div className={styles.deadlineTime}>{dl.time}</div>}
                        </>
                      )}
                    </td>
                    <td className={styles.arrowCell}>
                      <span className={styles.arrowBtn}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MyHomeworksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const reviewReturnHref = useMemo(() => {
    const s = searchParams.toString();
    return s ? `/app/homeworks?${s}` : '/app/homeworks';
  }, [searchParams]);

  const courseSlug = searchParams.get('course_slug') ?? undefined;
  const lessonSlug = searchParams.get('lesson_slug') ?? undefined;

  const coursesQuery = useCoursesForHome();
  const courseHomeQuery = useCourseHomeBySlug(courseSlug);
  const homeworksQuery = useMyHomeworks(courseSlug, lessonSlug);

  const courses = coursesQuery.data ?? [];
  const selectedCourse = courses.find((c) => c.slug === courseSlug);
  const selectedLesson = courseHomeQuery.data?.content
    .flatMap((s) => s.lessons)
    .find((l) => l.slug === lessonSlug);

  const availableLessons = useMemo<Array<{ slug: string; title: string }>>(() => {
    if (!courseHomeQuery.data) return [];
    return courseHomeQuery.data.content.flatMap((section) =>
      section.lessons.map((l) => ({ slug: l.slug, title: l.title })),
    );
  }, [courseHomeQuery.data]);

  function setFilter(key: 'course_slug' | 'lesson_slug', value: string | undefined) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key === 'course_slug') next.delete('lesson_slug');
      return next;
    });
  }

  function renderContent() {
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
      return <StudentView items={homeworksQuery.data.my_attempts.items} />;
    }
    return (
      <TeacherView
        items={homeworksQuery.data.student_attempts.items}
        reviewReturnHref={reviewReturnHref}
      />
    );
  }

  return (
    <PageFrame>
      <div className={styles.wrap}>
        {/* Breadcrumb */}
        <nav className={styles.breadcrumb}>
          <Link to="/app"><Home size={14} /></Link>
          {selectedCourse && (
            <>
              <span className={styles.breadcrumbSep}>›</span>
              <span>{selectedCourse.title}</span>
            </>
          )}
          {selectedLesson && (
            <>
              <span className={styles.breadcrumbSep}>›</span>
              <span className={styles.breadcrumbCurrent}>{selectedLesson.title}</span>
            </>
          )}
        </nav>

        {/* Selectors */}
        <div className={styles.selectors}>
          <Select
            value={courseSlug ?? '__all__'}
            onValueChange={(val) => setFilter('course_slug', val === '__all__' ? undefined : val)}
          >
            <SelectTrigger className={styles.selectorTrigger}>
              <SelectValue placeholder="Выберите курс" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Все курсы</SelectItem>
              {courses.map((c) => (
                <SelectItem key={c.slug} value={c.slug}>{c.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={lessonSlug ?? '__all__'}
            onValueChange={(val) => setFilter('lesson_slug', val === '__all__' ? undefined : val)}
            disabled={!courseSlug}
          >
            <SelectTrigger className={styles.selectorTrigger}>
              <SelectValue placeholder={courseSlug ? 'Все уроки' : 'Сначала выберите курс'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Все уроки</SelectItem>
              {availableLessons.map((l) => (
                <SelectItem key={l.slug} value={l.slug}>{l.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {renderContent()}
      </div>
    </PageFrame>
  );
}
