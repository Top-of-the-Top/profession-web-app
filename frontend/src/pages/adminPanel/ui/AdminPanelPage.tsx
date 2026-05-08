import { useState } from 'react';
import { BookOpen, Users, Mail, Plus, Trash2, Eye, EyeOff, UserPlus, UserMinus, Pencil, X, Check } from 'lucide-react';
import { Spinner } from '@shared/ui';
import { cn } from '@shared/lib/utils';
import { useAdminCourses, useAdminTeachers, useAdminInvites, type AdminCourse, type AdminTeacher } from '@shared/api/queries/adminPanel';
import {
  useCreateCourse,
  usePatchAdminCourse,
  useDeleteAdminCourse,
  usePublishCourse,
  useUnpublishCourse,
  useAddCourseAuthor,
  useRemoveCourseAuthor,
  useSendInvite,
} from '@shared/api/mutations/adminPanel';
import styles from './AdminPanelPage.module.css';

type Tab = 'courses' | 'teachers' | 'invites';

export default function AdminPanelPage() {
  const [tab, setTab] = useState<Tab>('courses');

  return (
    <div className={styles.page}>
      <div className={styles.wrap}>
        <h1 className={styles.pageTitle}>Админ-панель</h1>

        <div className={styles.tabBar}>
          <button
            className={cn(styles.tabBtn, tab === 'courses' && styles.tabBtnActive)}
            onClick={() => setTab('courses')}
          >
            <BookOpen size={16} />
            Курсы
          </button>
          <button
            className={cn(styles.tabBtn, tab === 'teachers' && styles.tabBtnActive)}
            onClick={() => setTab('teachers')}
          >
            <Users size={16} />
            Преподаватели
          </button>
          <button
            className={cn(styles.tabBtn, tab === 'invites' && styles.tabBtnActive)}
            onClick={() => setTab('invites')}
          >
            <Mail size={16} />
            Приглашения
          </button>
        </div>

        <div className={styles.tabContent}>
          {tab === 'courses' && <CoursesTab />}
          {tab === 'teachers' && <TeachersTab />}
          {tab === 'invites' && <InvitesTab />}
        </div>
      </div>
    </div>
  );
}

function CoursesTab() {
  const { data: courses, isLoading, error } = useAdminCourses();
  const { data: teachers } = useAdminTeachers();
  const createCourse = useCreateCourse();
  const deleteCourse = useDeleteAdminCourse();
  const publishCourse = usePublishCourse();
  const unpublishCourse = useUnpublishCourse();

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ title: '', sub_title: '', description: '', price: '', starts_at: '', duration_weeks: '', min_age: '' });
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [managingSlug, setManagingSlug] = useState<string | null>(null);

  function handleCreate() {
    createCourse.mutate(
      {
        title: createForm.title,
        sub_title: createForm.sub_title,
        description: createForm.description,
        price: Number(createForm.price),
        starts_at: createForm.starts_at || null,
        duration_weeks: createForm.duration_weeks ? Number(createForm.duration_weeks) : null,
        min_age: createForm.min_age ? Number(createForm.min_age) : null,
      },
      {
        onSuccess: () => {
          setShowCreate(false);
          setCreateForm({ title: '', sub_title: '', description: '', price: '', starts_at: '', duration_weeks: '', min_age: '' });
        },
      },
    );
  }

  if (isLoading) return <div className={styles.centered}><Spinner size="lg" /></div>;
  if (error) return <div className={styles.errorMsg}>Ошибка загрузки курсов</div>;

  return (
    <div className={styles.tabContent}>
      <div className={styles.actionRow}>
        <button className={styles.btnPrimary} onClick={() => setShowCreate(!showCreate)}>
          <Plus size={16} />
          Новый курс
        </button>
      </div>

      {showCreate && (
        <div className={styles.formCard}>
          <h3 className={styles.formTitle}>Создать курс</h3>
          <div className={styles.formGrid}>
            <label className={styles.formLabel}>
              Название
              <input
                className={styles.formInput}
                value={createForm.title}
                onChange={(e) => setCreateForm((p) => ({ ...p, title: e.target.value }))}
                placeholder="Название курса"
              />
            </label>
            <label className={styles.formLabel}>
              Краткое описание
              <input
                className={styles.formInput}
                value={createForm.sub_title}
                onChange={(e) => setCreateForm((p) => ({ ...p, sub_title: e.target.value }))}
                placeholder="Краткое описание"
              />
            </label>
            <label className={styles.formLabel}>
              Цена (₽)
              <input
                className={styles.formInput}
                type="number"
                min="0"
                value={createForm.price}
                onChange={(e) => setCreateForm((p) => ({ ...p, price: e.target.value }))}
                placeholder="0"
              />
            </label>
            <label className={styles.formLabel}>
              Дата старта
              <input
                className={styles.formInput}
                type="date"
                value={createForm.starts_at}
                onChange={(e) => setCreateForm((p) => ({ ...p, starts_at: e.target.value }))}
              />
            </label>
            <label className={styles.formLabel}>
              Длительность (недели)
              <input
                className={styles.formInput}
                type="number"
                min="1"
                value={createForm.duration_weeks}
                onChange={(e) => setCreateForm((p) => ({ ...p, duration_weeks: e.target.value }))}
                placeholder="—"
              />
            </label>
            <label className={styles.formLabel}>
              Мин. возраст
              <input
                className={styles.formInput}
                type="number"
                min="0"
                value={createForm.min_age}
                onChange={(e) => setCreateForm((p) => ({ ...p, min_age: e.target.value }))}
                placeholder="—"
              />
            </label>
            <label className={cn(styles.formLabel, styles.formLabelFull)}>
              Описание
              <textarea
                className={styles.formTextarea}
                value={createForm.description}
                onChange={(e) => setCreateForm((p) => ({ ...p, description: e.target.value }))}
                placeholder="Полное описание курса"
                rows={3}
              />
            </label>
          </div>
          <div className={styles.formActions}>
            <button
              className={styles.btnPrimary}
              onClick={handleCreate}
              disabled={createCourse.isPending || !createForm.title.trim()}
            >
              {createCourse.isPending ? <Spinner size="sm" /> : 'Создать'}
            </button>
            <button className={styles.btnSecondary} onClick={() => setShowCreate(false)}>
              Отмена
            </button>
          </div>
        </div>
      )}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Название</th>
              <th className={cn(styles.th, styles.thStatus)}>Статус</th>
              <th className={styles.th}>Цена</th>
              <th className={styles.th}>Авторы</th>
              <th className={styles.th}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {!courses?.length && (
              <tr><td className={styles.emptyCell} colSpan={5}>Нет курсов</td></tr>
            )}
            {courses?.map((course) => (
              <>
                <tr key={course.course_id} className={styles.tr}>
                  <td className={styles.td}>
                    <div className={styles.courseTitle}>{course.title}</div>
                    <div className={styles.courseSubtitle}>{course.sub_title}</div>
                  </td>
                  <td className={styles.td}>
                    <span className={cn(styles.badge, course.type === 'published' ? styles.badgeGreen : styles.badgeGray)}>
                      {course.type === 'published' ? 'Опубликован' : 'Черновик'}
                    </span>
                  </td>
                  <td className={styles.tdNum}>{course.price.toLocaleString('ru')} ₽</td>
                  <td className={styles.td}>
                    <div className={styles.authorsList}>
                      {(course.authors as unknown as AdminTeacher[]).map((a) => (
                        <span key={a.id} className={styles.authorChip}>
                          {a.first_name} {a.last_name}
                        </span>
                      ))}
                      {!(course.authors as unknown as AdminTeacher[]).length && (
                        <span className={styles.noAuthors}>—</span>
                      )}
                    </div>
                  </td>
                  <td className={styles.tdActions}>
                    <div className={styles.tdActionsInner}>
                      <button
                        className={styles.iconBtn}
                        title="Редактировать"
                        onClick={() => setEditingSlug(editingSlug === course.slug ? null : course.slug)}
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        type="button"
                        className={cn(styles.publishToggle, course.type === 'published' && styles.publishToggleOn)}
                        title={course.type === 'published' ? 'Снять с публикации' : 'Опубликовать'}
                        onClick={() =>
                          course.type === 'draft'
                            ? publishCourse.mutate(course.slug)
                            : unpublishCourse.mutate(course.slug)
                        }
                        disabled={publishCourse.isPending || unpublishCourse.isPending}
                      >
                        <span className={styles.publishToggleThumb}>
                          {course.type === 'published' ? <Eye size={12} /> : <EyeOff size={12} />}
                        </span>
                      </button>
                      <button
                        className={cn(styles.iconBtn, styles.iconBtnBlue)}
                        title="Управление авторами"
                        onClick={() => setManagingSlug(managingSlug === course.slug ? null : course.slug)}
                      >
                        <Users size={15} />
                      </button>
                      <button
                        className={cn(styles.iconBtn, styles.iconBtnRed)}
                        title="Удалить"
                        onClick={() => { if (confirm('Удалить курс?')) deleteCourse.mutate(course.slug); }}
                        disabled={deleteCourse.isPending}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
                {editingSlug === course.slug && (
                  <tr key={`edit-${course.course_id}`}>
                    <td colSpan={5} className={styles.expandedCell}>
                      <EditCourseForm course={course} onClose={() => setEditingSlug(null)} />
                    </td>
                  </tr>
                )}
                {managingSlug === course.slug && (
                  <tr key={`manage-${course.course_id}`}>
                    <td colSpan={5} className={styles.expandedCell}>
                      <ManageAuthorsPanel course={course} teachers={teachers ?? []} onClose={() => setManagingSlug(null)} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EditCourseForm({ course, onClose }: { course: AdminCourse; onClose: () => void }) {
  const [form, setForm] = useState({
    title: course.title,
    sub_title: course.sub_title,
    price: String(course.price),
  });
  const patch = usePatchAdminCourse(course.slug);

  function handleSave() {
    patch.mutate(
      { title: form.title, sub_title: form.sub_title, price: Number(form.price) },
      { onSuccess: onClose },
    );
  }

  return (
    <div className={styles.expandedForm}>
      <div className={styles.formGrid}>
        <label className={styles.formLabel}>
          Название
          <input
            className={styles.formInput}
            value={form.title}
            onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
          />
        </label>
        <label className={styles.formLabel}>
          Краткое описание
          <input
            className={styles.formInput}
            value={form.sub_title}
            onChange={(e) => setForm((p) => ({ ...p, sub_title: e.target.value }))}
          />
        </label>
        <label className={styles.formLabel}>
          Цена (₽)
          <input
            className={styles.formInput}
            type="number"
            min="0"
            value={form.price}
            onChange={(e) => setForm((p) => ({ ...p, price: e.target.value }))}
          />
        </label>
      </div>
      <div className={styles.formActions}>
        <button className={styles.btnPrimary} onClick={handleSave} disabled={patch.isPending || !form.title.trim()}>
          {patch.isPending ? <Spinner size="sm" /> : <><Check size={14} /> Сохранить</>}
        </button>
        <button className={styles.btnSecondary} onClick={onClose}>
          <X size={14} /> Отмена
        </button>
      </div>
    </div>
  );
}

function ManageAuthorsPanel({
  course,
  teachers,
  onClose,
}: {
  course: AdminCourse;
  teachers: AdminTeacher[];
  onClose: () => void;
}) {
  const addAuthor = useAddCourseAuthor(course.slug);
  const removeAuthor = useRemoveCourseAuthor(course.slug);
  const courseAuthors = course.authors as unknown as AdminTeacher[];
  const courseAuthorIds = new Set(courseAuthors.map((a) => a.id));

  return (
    <div className={styles.expandedForm}>
      <div className={styles.managePanelHeader}>
        <span className={styles.managePanelTitle}>Управление авторами: {course.title}</span>
        <button className={styles.closeBtn} onClick={onClose}><X size={16} /></button>
      </div>
      <div className={styles.teacherManageList}>
        {!teachers.length && <div className={styles.emptyMsg}>Нет преподавателей на платформе</div>}
        {teachers.map((t) => {
          const isAuthor = courseAuthorIds.has(t.id);
          return (
            <div key={t.id} className={styles.teacherManageRow}>
              <div className={styles.teacherManageInfo}>
                <span className={styles.teacherName}>{t.first_name} {t.last_name}</span>
                <span className={styles.teacherEmail}>{t.email ?? '—'}</span>
              </div>
              {isAuthor ? (
                <button
                  className={cn(styles.iconBtn, styles.iconBtnOrange)}
                  title="Снять с курса"
                  onClick={() => removeAuthor.mutate(t.id)}
                  disabled={removeAuthor.isPending}
                >
                  <UserMinus size={15} />
                </button>
              ) : (
                <button
                  className={cn(styles.iconBtn, styles.iconBtnGreen)}
                  title="Добавить на курс"
                  onClick={() => addAuthor.mutate(t.id)}
                  disabled={addAuthor.isPending}
                >
                  <UserPlus size={15} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TeachersTab() {
  const { data: teachers, isLoading, error } = useAdminTeachers();

  if (isLoading) return <div className={styles.centered}><Spinner size="lg" /></div>;
  if (error) return <div className={styles.errorMsg}>Ошибка загрузки преподавателей</div>;

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Имя</th>
            <th className={styles.th}>Email</th>
          </tr>
        </thead>
        <tbody>
          {!teachers?.length && (
            <tr><td className={styles.emptyCell} colSpan={2}>Нет преподавателей</td></tr>
          )}
          {teachers?.map((t) => (
            <tr key={t.id} className={styles.tr}>
              <td className={styles.td}>{t.first_name} {t.last_name || '—'}</td>
              <td className={styles.tdMono}>{t.email ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InvitesTab() {
  const { data: invites, isLoading, error } = useAdminInvites();
  const sendInvite = useSendInvite();
  const [email, setEmail] = useState('');

  function handleSend() {
    if (!email.trim()) return;
    sendInvite.mutate(email.trim(), { onSuccess: () => setEmail('') });
  }

  const statusLabel: Record<string, string> = {
    pending: 'Отправлено',
    used: 'Использовано',
    expired: 'Истекло',
  };
  const statusStyle: Record<string, string> = {
    pending: styles.badgeGreen,
    used: styles.badgeBlue,
    expired: styles.badgeGray,
  };

  if (isLoading) return <div className={styles.centered}><Spinner size="lg" /></div>;
  if (error) return <div className={styles.errorMsg}>Ошибка загрузки приглашений</div>;

  return (
    <div className={styles.tabContent}>
      <div className={styles.inviteFormRow}>
        <input
          className={styles.filterInput}
          type="email"
          placeholder="Email преподавателя"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
        />
        <button
          className={styles.btnPrimary}
          onClick={handleSend}
          disabled={sendInvite.isPending || !email.trim()}
        >
          {sendInvite.isPending ? <Spinner size="sm" /> : <><Mail size={15} /> Отправить</>}
        </button>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Email</th>
              <th className={styles.th}>Отправил</th>
              <th className={styles.th}>Создано</th>
              <th className={styles.th}>Истекает</th>
              <th className={styles.th}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {!invites?.length && (
              <tr><td className={styles.emptyCell} colSpan={5}>Нет приглашений</td></tr>
            )}
            {invites?.map((inv) => (
              <tr key={inv.id} className={styles.tr}>
                <td className={styles.td}>{inv.email}</td>
                <td className={styles.td}>
                  {inv.created_by
                    ? `${inv.created_by.first_name} ${inv.created_by.last_name}`.trim() || '—'
                    : '—'}
                </td>
                <td className={styles.tdMono}>{fmtDate(inv.created_at)}</td>
                <td className={styles.tdMono}>{fmtDate(inv.expires_at)}</td>
                <td className={styles.td}>
                  <span className={cn(styles.badge, statusStyle[inv.status] ?? styles.badgeGray)}>
                    {statusLabel[inv.status] ?? inv.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
