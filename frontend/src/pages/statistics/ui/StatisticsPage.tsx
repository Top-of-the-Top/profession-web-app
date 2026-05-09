import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart2, Users, BookOpen, GraduationCap, Search } from 'lucide-react';
import { PageFrame, Spinner } from '@shared/ui';
import { useRole } from '@shared/lib/rbac';
import {
  useStatWebinars,
  useStatStudents,
  useStatSchoolCourses,
  useStatSchoolTeachers,
  type StatWebinar,
  type StatStudent,
  type StatSchoolCourse,
  type StatSchoolTeacher,
  type UserBrief,
} from '@shared/api/queries/statistics';
import { cn } from '@shared/lib/utils';
import styles from './StatisticsPage.module.css';

function pct(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

function formatDateShort(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

type SortDir = 'asc' | 'desc';

function useSortState<K extends string>(initial: K) {
  const [key, setKey] = useState<K>(initial);
  const [dir, setDir] = useState<SortDir>('desc');
  const toggle = (k: K) => {
    if (k === key) setDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setKey(k); setDir('desc'); }
  };
  return { key, dir, toggle };
}

function SortTh<K extends string>({
  label, sortKey, current, dir, onSort, extraClass,
}: {
  label: string;
  sortKey: K;
  current: K;
  dir: SortDir;
  onSort: (k: K) => void;
  extraClass?: string;
}) {
  const active = sortKey === current;
  return (
    <th
      className={cn(styles.th, styles.thSortable, active && styles.thActive, extraClass)}
      onClick={() => onSort(sortKey)}
    >
      {label}
      <span className={styles.sortArrow}>{active ? (dir === 'desc' ? ' ↓' : ' ↑') : ' ↕'}</span>
    </th>
  );
}

function NumCellWithPopup({
  count,
  total,
  users,
  popupAlign = 'left',
}: {
  count: number;
  total: number;
  users: UserBrief[];
  popupAlign?: 'left' | 'right';
}) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className={styles.numCell}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span className={styles.numCellCount}>
        {count} <span className={styles.fractionSlash}>/</span> {total}
      </span>
      {total > 0 && (
        <span className={styles.subPct}>
          {` (${Math.round((count / total) * 100)}%)`}
        </span>
      )}
      {open && users.length > 0 && (
        <div className={cn(styles.numPopup, popupAlign === 'right' && styles.numPopupRight)}>
          {users.map((u) => (
            <div key={u.user_id} className={styles.numPopupItem}>
              {u.full_name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WebinarsTab({ isModerator }: { isModerator: boolean }) {
  const [courseTitleFilter, setCourseTitleFilter] = useState('');
  const [debouncedCourseTitle, setDebouncedCourseTitle] = useState('');
  const today = useMemo(() => new Date(), []);
  const from30 = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - 30);
    return d.toISOString();
  }, [today]);
  const to = useMemo(() => today.toISOString(), [today]);

  useMemo(() => {
    const t = setTimeout(() => setDebouncedCourseTitle(courseTitleFilter), 300);
    return () => clearTimeout(t);
  }, [courseTitleFilter]);

  const { data, isLoading, isError } = useStatWebinars(
    debouncedCourseTitle || undefined,
    from30,
    to,
  );

  const sort = useSortState<keyof StatWebinar>('started_at');

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const av = a[sort.key] ?? '';
      const bv = b[sort.key] ?? '';
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [data, sort.key, sort.dir]);

  return (
    <div className={styles.tabContent}>
      <div className={styles.filterRow}>
        <input
          type="text"
          className={styles.filterInput}
          placeholder="Название курса..."
          value={courseTitleFilter}
          onChange={(e) => setCourseTitleFilter(e.target.value)}
        />
      </div>

      {isLoading && <div className={styles.centered}><Spinner /></div>}
      {isError && <div className={styles.errorMsg}>Нет доступа или ошибка загрузки.</div>}

      {!isLoading && !isError && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortTh label="Курс" sortKey="course_title" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Урок" sortKey="lesson_title" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Начало" sortKey="started_at" current={sort.key} dir={sort.dir} onSort={sort.toggle} extraClass={styles.thCenter} />
                <SortTh label="Конец" sortKey="ended_at" current={sort.key} dir={sort.dir} onSort={sort.toggle} extraClass={styles.thCenter} />
                <th className={cn(styles.th, styles.thCenter)}>Заходили</th>
                <th className={cn(styles.th, styles.thCenter)}>Досмотрели 70%</th>
                <th className={cn(styles.th, styles.thRight)}>Сдали ДЗ</th>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr>
                  <td colSpan={7} className={styles.emptyCell}>Нет вебинаров за период</td>
                </tr>
              ) : (
                sorted.map((w) => (
                  <tr key={w.webinar_id} className={styles.tr}>
                    <td className={styles.td}>{w.course_title}</td>
                    <td className={styles.td}>{w.lesson_title}</td>
                    <td className={cn(styles.tdMono, styles.tdCenter)}><span className={styles.dateCell}>{formatDateShort(w.started_at)}</span></td>
                    <td className={cn(styles.tdMono, styles.tdCenter)}><span className={styles.dateCell}>{formatDateShort(w.ended_at)}</span></td>
                    <td className={cn(styles.tdNum, styles.tdCenter)}>
                      <NumCellWithPopup count={w.attended_any} total={w.attended_total} users={w.attended_any_users} />
                    </td>
                    <td className={cn(styles.tdNum, styles.tdCenter)}>
                      <NumCellWithPopup count={w.attended_threshold} total={w.attended_total} users={w.attended_threshold_users} />
                    </td>
                    <td className={cn(styles.tdNum, styles.tdRight)}>
                      <NumCellWithPopup count={w.homework_submitted_count} total={w.attended_total} users={w.homework_submitted_users} popupAlign="right" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StudentsTab() {
  const navigate = useNavigate();
  const [courseTitleFilter, setCourseTitleFilter] = useState('');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [debouncedCourseTitle, setDebouncedCourseTitle] = useState('');

  useMemo(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useMemo(() => {
    const t = setTimeout(() => setDebouncedCourseTitle(courseTitleFilter), 300);
    return () => clearTimeout(t);
  }, [courseTitleFilter]);

  const { data, isLoading, isError } = useStatStudents(
    debouncedCourseTitle || undefined,
    debouncedSearch || undefined,
  );

  return (
    <div className={styles.tabContent}>
      <div className={styles.filterRow}>
        <div className={styles.searchWrap}>
          <Search size={16} className={styles.searchIcon} />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Поиск по ФИО, email, телефону..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <input
          type="text"
          className={styles.filterInput}
          placeholder="Название курса..."
          value={courseTitleFilter}
          onChange={(e) => setCourseTitleFilter(e.target.value)}
        />
      </div>

      {isLoading && <div className={styles.centered}><Spinner /></div>}
      {isError && <div className={styles.errorMsg}>Нет доступа или ошибка загрузки.</div>}

      {!isLoading && !isError && (
        <div className={styles.studentGrid}>
          {(!data || data.length === 0) ? (
            <div className={styles.emptyMsg}>Студенты не найдены</div>
          ) : (
            data.map((s) => (
              <StudentCard
                key={s.user_id}
                student={s}
                onOpenCard={(userId, courseId) =>
                  navigate(`/app/statistics/students/${userId}/courses/${courseId}`)
                }
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

function StudentCard({
  student,
  onOpenCard,
}: {
  student: StatStudent;
  onOpenCard: (userId: number, courseId: string) => void;
}) {
  return (
    <div className={styles.studentCard}>
      <div className={styles.studentCardHeader}>
        <div className={styles.studentAvatar}>
          {student.full_name !== '—'
            ? student.full_name.split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase()
            : '?'}
        </div>
        <div className={styles.studentCardInfo}>
          <span className={styles.studentName}>{student.full_name}</span>
          {student.email && <span className={styles.studentContact}>{student.email}</span>}
          {student.phone && <span className={styles.studentContact}>{student.phone}</span>}
        </div>
      </div>
      {student.courses.length > 0 && (
        <div className={styles.studentCourses}>
          {student.courses.map((c) => (
            <button
              key={c.course_id}
              type="button"
              className={styles.coursePill}
              onClick={() => onOpenCard(student.user_id, c.course_id)}
            >
              {c.title}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SchoolCoursesTab() {
  const { data, isLoading, isError } = useStatSchoolCourses();
  const sort = useSortState<keyof StatSchoolCourse>('students');

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const av = a[sort.key] ?? 0;
      const bv = b[sort.key] ?? 0;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [data, sort.key, sort.dir]);

  return (
    <div className={styles.tabContent}>
      {isLoading && <div className={styles.centered}><Spinner /></div>}
      {isError && <div className={styles.errorMsg}>Нет доступа или ошибка загрузки.</div>}
      {!isLoading && !isError && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortTh label="Курс" sortKey="title" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Студентов" sortKey="students" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Прогресс" sortKey="avg_progress" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Посещаемость" sortKey="avg_attendance" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Сдача ДЗ" sortKey="avg_homework" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr><td colSpan={5} className={styles.emptyCell}>Нет данных</td></tr>
              ) : (
                sorted.map((c) => (
                  <tr key={c.course_id} className={styles.tr}>
                    <td className={styles.td}>{c.title}</td>
                    <td className={styles.tdNum}>{c.students}</td>
                    <td className={styles.tdNum}>
                      <ProgressBar value={c.avg_progress} />
                    </td>
                    <td className={styles.tdNum}>
                      <ProgressBar value={c.avg_attendance} color="#3b6ff5" />
                    </td>
                    <td className={styles.tdNum}>
                      <ProgressBar value={c.avg_homework} color="#22c55e" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ProgressBar({ value, color = '#211c84' }: { value: number; color?: string }) {
  const p = Math.round(value * 100);
  return (
    <div className={styles.progressCell}>
      <div className={styles.progressBarTrack}>
        <div
          className={styles.progressBarFill}
          style={{ width: `${p}%`, background: color }}
        />
      </div>
      <span className={styles.progressLabel}>{p}%</span>
    </div>
  );
}

function SchoolTeachersTab() {
  const { data, isLoading, isError } = useStatSchoolTeachers();
  const sort = useSortState<keyof StatSchoolTeacher>('reviewed_30d');

  const sorted = useMemo(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const av = a[sort.key] ?? '';
      const bv = b[sort.key] ?? '';
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.dir === 'asc' ? cmp : -cmp;
    });
  }, [data, sort.key, sort.dir]);

  return (
    <div className={styles.tabContent}>
      {isLoading && <div className={styles.centered}><Spinner /></div>}
      {isError && <div className={styles.errorMsg}>Нет доступа или ошибка загрузки.</div>}
      {!isLoading && !isError && (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortTh label="Преподаватель" sortKey="full_name" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Проверено за 7 дней" sortKey="reviewed_7d" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Проверено за 30 дней" sortKey="reviewed_30d" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
                <SortTh label="Последний вход" sortKey="last_login" current={sort.key} dir={sort.dir} onSort={sort.toggle} />
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr><td colSpan={4} className={styles.emptyCell}>Нет данных</td></tr>
              ) : (
                sorted.map((t) => (
                  <tr key={t.user_id} className={styles.tr}>
                    <td className={styles.td}>{t.full_name}</td>
                    <td className={styles.tdNum}>{t.reviewed_7d}</td>
                    <td className={styles.tdNum}>{t.reviewed_30d}</td>
                    <td className={styles.tdMono}>
                      {t.last_login ? formatDateShort(t.last_login) : 'Никогда'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

type Tab = 'webinars' | 'students' | 'school-courses' | 'school-teachers';

const TABS_TEACHER: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'webinars', label: 'Уроки', icon: BarChart2 },
  { id: 'students', label: 'Студенты', icon: Users },
];

const TABS_MODERATOR: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'webinars', label: 'Уроки', icon: BarChart2 },
  { id: 'students', label: 'Студенты', icon: Users },
  { id: 'school-courses', label: 'Курсы школы', icon: BookOpen },
  { id: 'school-teachers', label: 'Преподаватели', icon: GraduationCap },
];

export default function StatisticsPage() {
  const { is } = useRole();
  const isModerator = is.moderator;

  const tabs = isModerator ? TABS_MODERATOR : TABS_TEACHER;
  const [activeTab, setActiveTab] = useState<Tab>('webinars');

  const safeTab = tabs.some((t) => t.id === activeTab) ? activeTab : tabs[0].id;

  return (
    <PageFrame>
      <div className={styles.page}>
        <div className={styles.wrap}>
          <h1 className={styles.pageTitle}>Статистика</h1>

          <div className={styles.tabBar}>
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={cn(styles.tabBtn, safeTab === id && styles.tabBtnActive)}
                onClick={() => setActiveTab(id)}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </div>

          {safeTab === 'webinars' && <WebinarsTab isModerator={isModerator} />}
          {safeTab === 'students' && <StudentsTab />}
          {safeTab === 'school-courses' && isModerator && <SchoolCoursesTab />}
          {safeTab === 'school-teachers' && isModerator && <SchoolTeachersTab />}
        </div>
      </div>
    </PageFrame>
  );
}
