import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Home, BookOpen, ClipboardList, Check, X, Copy } from 'lucide-react';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  Button,
  CenteredMessageBlock,
  PageFrame,
  Spinner,
} from '@shared/ui';
import { useCourseHomeBySlug } from '@shared/api/queries/courses';
import { useApplications } from '@shared/api/queries/applications';
import { useApproveApplication, useRejectApplication } from '@shared/api/mutations/applications';
import { useRole } from '@shared/lib/rbac/useRole';
import { cn } from '@shared/lib/utils';
import { AiChatPanel } from '../../../features/ai-chat';
import { AddSectionRow } from './components/AddSectionRow';
import { SectionBlock } from './components/SectionBlock';
import styles from './CourseLessonsPage.module.css';

const STREAK_FIRE_SRC = `${import.meta.env.BASE_URL}course/yellow-fire.svg`;

function StreakCard({ streakDays = 13 }: { streakDays?: number }) {
  return (
    <div className={cn(styles.sideCard, styles.streakCard)}>
      <div className={styles.streakCardLayout}>
        <div className={styles.streakCardTextCol}>
          <p className={styles.streakCardTitle}>
            Ваша серия
            <br />
            вебинаров
          </p>
          <p className={styles.streakCardSubtitle}>
            Не пропусти следующий,
            <br />
            чтобы серия росла
          </p>
        </div>
        <div className={styles.streakVisualCol}>
          <span className={styles.streakNumber}>{streakDays}</span>
          <img
            src={STREAK_FIRE_SRC}
            alt=""
            className={styles.streakFireImg}
            width={58}
            height={107}
            decoding="async"
          />
        </div>
      </div>
    </div>
  );
}

function StudentProgressCard({
  lessonsDone,
  lessonsTotal,
  homeworkDone,
  homeworkTotal,
}: {
  lessonsDone: number;
  lessonsTotal: number;
  homeworkDone: number;
  homeworkTotal: number;
}) {
  const lessonsPct =
    lessonsTotal > 0 ? Math.round((lessonsDone / lessonsTotal) * 100) : 0;
  const hwPct =
    homeworkTotal > 0 ? Math.round((homeworkDone / homeworkTotal) * 100) : 0;

  return (
    <div
      className={cn(
        styles.sideCard,
        styles.statSidebarCard,
        styles.studentProgressCard
      )}
    >
      <div className={styles.progressCardHead}>
        <span className={styles.progressLiveDot} aria-hidden />
        <p className={styles.progressCardTitle}>Ваш прогресс</p>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Пройдено уроков</span>
          <span className={styles.progressValue}>
            {lessonsDone}/{lessonsTotal}
          </span>
        </div>
        <div className={styles.progressTrack}>
          <div
            className={styles.progressFillStudent}
            style={{ width: `${lessonsPct}%` }}
          />
        </div>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Сдано заданий</span>
          <span className={styles.progressValue}>
            {homeworkDone}/{homeworkTotal}
          </span>
        </div>
        <div className={styles.progressTrack}>
          <div
            className={styles.progressFillStudent}
            style={{ width: `${hwPct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function StaffStatsCard({
  attendanceRate,
  homeworkRate,
}: {
  attendanceRate: number;
  homeworkRate: number;
}) {
  const attendancePct = Math.round(attendanceRate * 100);
  const homeworkPct = Math.round(homeworkRate * 100);
  return (
    <div className={styles.sideCard}>
			 <div className={styles.progressCardHead}>
        <span className={styles.progressLiveDot} aria-hidden />
        <p className={styles.progressCardTitle}>Статистика</p>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Посещаемость вебинаров</span>
          <span className={styles.progressValue}>{attendancePct}%</span>
        </div>
        <div className={styles.progressTrack}>
          <div className={styles.progressFillDark} style={{ width: `${attendancePct}%` }} />
        </div>
      </div>
      <div className={styles.progressBlock}>
        <div className={styles.progressHeader}>
          <span>Сдача ДЗ</span>
          <span className={styles.progressValue}>{homeworkPct}%</span>
        </div>
        <div className={styles.progressTrack}>
          <div className={styles.progressFillDark} style={{ width: `${homeworkPct}%` }} />
        </div>
      </div>
    </div>
  );
}

function ApplicationsPanel({ courseSlug }: { courseSlug: string }) {
  const { data: applications, isLoading } = useApplications(courseSlug);
  const approve = useApproveApplication(courseSlug);
  const reject = useRejectApplication(courseSlug);
  const [copied, setCopied] = useState(false);

  function copyLink() {
    void navigator.clipboard.writeText(`${window.location.origin}/app/store/${courseSlug}`).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className={styles.appsTable}>
      <div className={styles.appsTableActions}>
        <button type="button" className={styles.appsCopyBtn} onClick={copyLink}>
          <Copy size={15} />
          {copied ? 'Скопировано!' : 'Скопировать ссылку на запись'}
        </button>
      </div>
      {isLoading && <div className={styles.appsPanelEmpty}><Spinner /></div>}
      {!isLoading && !applications?.length && (
        <div className={styles.appsPanelEmpty}>Заявок пока нет</div>
      )}
      {!isLoading && !!applications?.length && (
        <>
          <div className={styles.appsTableHeader}>
            <span>Студент</span>
            <span>Email</span>
            <span>Дата подачи</span>
            <span>Статус</span>
            <span />
          </div>
          {applications.map((app) => (
            <div key={app.application_id} className={styles.appsTableRow}>
              <span className={styles.appsName}>
                {app.user.first_name} {app.user.last_name}
              </span>
              <span className={styles.appsEmail}>{app.user.email}</span>
              <span className={styles.appsDate}>
                {new Date(app.created_at).toLocaleDateString('ru-RU')}
              </span>
              <span className={cn(styles.appsStatus, styles[`appsStatus_${app.status}`])}>
                {app.status === 'pending' ? 'На рассмотрении' : app.status === 'approved' ? 'Принята' : 'Отклонена'}
              </span>
              <span className={styles.appsActions}>
                {app.status === 'pending' && (
                  <>
                    <button
                      type="button"
                      className={cn(styles.appsActionBtn, styles.appsActionApprove)}
                      disabled={approve.isPending || reject.isPending}
                      onClick={() => approve.mutate(app.application_id)}
                      title="Принять"
                    >
                      <Check size={15} />
                    </button>
                    <button
                      type="button"
                      className={cn(styles.appsActionBtn, styles.appsActionReject)}
                      disabled={approve.isPending || reject.isPending}
                      onClick={() => reject.mutate(app.application_id)}
                      title="Отклонить"
                    >
                      <X size={15} />
                    </button>
                  </>
                )}
              </span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

type StaffTab = 'structure' | 'applications';

export default function CourseLessonsPage() {
  const { slug } = useParams<{ slug: string }>();
  const { hasAny } = useRole();
  const isStaff = hasAny('teacher', 'moderator');

  const homeQuery = useCourseHomeBySlug(slug);
  const { data: payload, isLoading, isError, refetch } = homeQuery;

  const title =
    (payload?.title && payload.title.trim() !== '' ? payload.title : null) ??
    slug?.replace(/-/g, ' ') ??
    'Курс';

  const { content, meta } = payload ?? { content: [], meta: { role: '' } };

  const [openSections, setOpenSections] = useState<Set<string>>(
    () => new Set()
  );
  const [staffTab, setStaffTab] = useState<StaffTab>('structure');

  const toggleSection = (sectionId: string, open: boolean) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (open) next.add(sectionId);
      else next.delete(sectionId);
      return next;
    });
  };

  if (!slug) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <CenteredMessageBlock
            message="Не указан адрес курса."
            actions={
              <Button type="button" variant="outline" asChild>
                <Link to="/app">На главную</Link>
              </Button>
            }
          />
        </div>
      </PageFrame>
    );
  }

  if (isLoading) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <Spinner />
        </div>
      </PageFrame>
    );
  }

  if (isError || !payload) {
    return (
      <PageFrame>
        <div className={styles.centered}>
          <CenteredMessageBlock
            message="Не удалось загрузить программу курса. Проверьте, что вы записаны на курс, и попробуйте снова."
            actions={
              <Button type="button" onClick={() => void refetch()}>
                Попробовать снова
              </Button>
            }
          />
        </div>
      </PageFrame>
    );
  }

  const staffMeta = meta.role === 'teacher_or_moderator' ? (meta as import('@shared/api/courseApi').CourseHomeMetaStaff) : null;
  const studentMeta = meta.role === 'student' ? (meta as import('@shared/api/courseApi').CourseHomeMetaStudent) : null;

  const breadcrumb = (
    <div className={styles.breadcrumbWrap}>
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/app" className={styles.homeLink} aria-label="Домашняя">
                <Home size={18} strokeWidth={2} />
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{title}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  );

  const sidebar = (
    <aside className={styles.sidebar}>
      {isStaff ? (
        <StaffStatsCard
          attendanceRate={staffMeta?.webinar_attendance_rate ?? 0}
          homeworkRate={staffMeta?.homework_completion_rate ?? 0}
        />
      ) : (
        <>
          {studentMeta && studentMeta.attendance_streak >= 2 && (
            <StreakCard streakDays={studentMeta.attendance_streak} />
          )}
          <StudentProgressCard
            lessonsDone={studentMeta?.lessons_completed ?? 0}
            lessonsTotal={studentMeta?.lessons_total ?? 0}
            homeworkDone={studentMeta?.homeworks_submitted ?? 0}
            homeworkTotal={studentMeta?.homeworks_total ?? 0}
          />
        </>
      )}
      <AiChatPanel courseSlug={slug} />
    </aside>
  );

  const structureContent = (
    <>
      {content.length === 0
        ? <div className={styles.empty}>В этом курсе пока нет разделов.</div>
        : content.map((section) => (
          <SectionBlock
            key={section.section_id}
            section={section}
            courseSlug={slug ?? ''}
            isStaff={isStaff}
            open={openSections.has(section.section_id)}
            onOpenChange={(o) => toggleSection(section.section_id, o)}
          />
        ))}
      {isStaff ? <AddSectionRow courseSlug={slug ?? ''} /> : null}
    </>
  );

  return (
    <PageFrame>
      {breadcrumb}
      <h1 className={styles.pageTitle}>{title}</h1>

      {isStaff && (
        <div className={styles.tabBar}>
          <button
            type="button"
            className={cn(styles.tabBtn, staffTab === 'structure' && styles.tabBtnActive)}
            onClick={() => setStaffTab('structure')}
          >
            <BookOpen size={16} />
            Структура
          </button>
          <button
            type="button"
            className={cn(styles.tabBtn, staffTab === 'applications' && styles.tabBtnActive)}
            onClick={() => setStaffTab('applications')}
          >
            <ClipboardList size={16} />
            Заявки
          </button>
        </div>
      )}

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          {!isStaff || staffTab === 'structure'
            ? structureContent
            : <ApplicationsPanel courseSlug={slug ?? ''} />}
        </div>
        {sidebar}
      </div>
    </PageFrame>
  );
}
