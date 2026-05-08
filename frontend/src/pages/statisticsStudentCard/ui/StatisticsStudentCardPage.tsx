import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CircleCheck, CircleDot, Circle, Video } from 'lucide-react';
import { PageFrame, Spinner } from '@shared/ui';
import { useStatStudentCard, type StatStudentCardHomework } from '@shared/api/queries/statistics';
import { cn } from '@shared/lib/utils';
import styles from './StatisticsStudentCardPage.module.css';

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

const HW_STATUS_LABEL: Record<StatStudentCardHomework['status'], string> = {
  not_started: 'не начато',
  draft: 'черновик',
  submitted: 'отправлено',
  reviewed: 'проверено',
};

const HW_STATUS_CLASS: Record<StatStudentCardHomework['status'], string> = {
  not_started: 'hwNone',
  draft: 'hwDraft',
  submitted: 'hwSubmitted',
  reviewed: 'hwReviewed',
};

function HomeworkTooltip({ homeworks }: { homeworks: StatStudentCardHomework[] }) {
  if (homeworks.length === 0) return <span className={styles.tooltipEmpty}>ДЗ нет</span>;
  return (
    <div className={styles.tooltipList}>
      {homeworks.map((hw) => (
        <div key={hw.homework_id} className={styles.tooltipItem}>
          <span className={cn(styles.hwDot, styles[HW_STATUS_CLASS[hw.status]])} />
          <span className={styles.tooltipTitle}>{hw.title || 'ДЗ'}</span>
          <span className={styles.tooltipStatus}>{HW_STATUS_LABEL[hw.status]}</span>
          {hw.status === 'reviewed' && hw.grade !== null && (
            <span className={styles.tooltipGrade}>{hw.grade} б.</span>
          )}
        </div>
      ))}
    </div>
  );
}

function HwCell({ homeworks }: { homeworks: StatStudentCardHomework[] }) {
  const [open, setOpen] = useState(false);
  const submitted = homeworks.filter(
    (hw) => hw.status === 'submitted' || hw.status === 'reviewed',
  ).length;
  const total = homeworks.length;

  return (
    <div
      className={styles.hwCell}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span className={styles.hwFraction}>
        {submitted}/{total}
      </span>
      {open && (
        <div className={styles.tooltipBox}>
          <HomeworkTooltip homeworks={homeworks} />
        </div>
      )}
    </div>
  );
}

export default function StatisticsStudentCardPage() {
  const { userId, courseId } = useParams<{ userId: string; courseId: string }>();
  const { data, isLoading, isError } = useStatStudentCard(userId, courseId);

  return (
    <PageFrame>
      <div className={styles.page}>
        <div className={styles.wrap}>
          <Link to="/app/statistics" className={styles.backLink}>
            <ArrowLeft size={16} />
            Назад к статистике
          </Link>

          {isLoading && (
            <div className={styles.centered}>
              <Spinner />
            </div>
          )}

          {isError && (
            <div className={styles.errorMsg}>
              Нет доступа или студент не найден.
            </div>
          )}

          {!isLoading && !isError && data && (
            <>
              <h1 className={styles.pageTitle}>
                Карточка студента #{data.student_id}
              </h1>
              <p className={styles.subTitle}>Курс: {data.course_id}</p>

              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.th}>Урок</th>
                      <th className={styles.th}>Вебинар</th>
                      <th className={styles.th}>ДЗ</th>
                      <th className={styles.th}>Пройден</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.lessons.map((lesson) => {
                      const webinar = lesson.webinar;
                      return (
                        <tr key={lesson.lesson_id} className={styles.tr}>
                          <td className={styles.td}>{lesson.lesson_title}</td>
                          <td className={styles.tdWebinar}>
                            {webinar === null ? (
                              <span className={styles.webinarNone}>—</span>
                            ) : webinar.kind === 'none' ? (
                              <span className={styles.webinarNone}>не был</span>
                            ) : (
                              <div className={styles.webinarInfo}>
                                <Video
                                  size={14}
                                  className={
                                    webinar.kind === 'live'
                                      ? styles.webinarIconLive
                                      : styles.webinarIconRec
                                  }
                                />
                                <span
                                  className={
                                    webinar.kind === 'live'
                                      ? styles.webinarKindLive
                                      : styles.webinarKindRec
                                  }
                                >
                                  {webinar.kind === 'live' ? 'live' : 'запись'}
                                </span>
                                <span className={styles.webinarPct}>
                                  {pct(webinar.watched_ratio)}
                                </span>
                              </div>
                            )}
                          </td>
                          <td className={styles.tdHw}>
                            <HwCell homeworks={lesson.homeworks} />
                          </td>
                          <td className={styles.tdCompleted}>
                            {lesson.is_completed ? (
                              <CircleCheck
                                size={18}
                                className={styles.completedYes}
                              />
                            ) : (
                              <Circle size={18} className={styles.completedNo} />
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className={styles.legend}>
                <div className={styles.legendItem}>
                  <span className={cn(styles.hwDot, styles.hwNone)} />
                  не начато
                </div>
                <div className={styles.legendItem}>
                  <span className={cn(styles.hwDot, styles.hwDraft)} />
                  черновик
                </div>
                <div className={styles.legendItem}>
                  <span className={cn(styles.hwDot, styles.hwSubmitted)} />
                  отправлено
                </div>
                <div className={styles.legendItem}>
                  <span className={cn(styles.hwDot, styles.hwReviewed)} />
                  проверено
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </PageFrame>
  );
}
