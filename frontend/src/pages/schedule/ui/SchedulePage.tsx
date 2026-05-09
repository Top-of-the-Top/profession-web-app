import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Clock, X } from 'lucide-react';
import { PageFrame, Spinner, Button } from '@shared/ui';
import { useSchedule } from '@shared/api/queries/schedule';
import type { ScheduleItem, WebinarScheduleItem, HomeworkScheduleItem } from '@shared/api/scheduleApi';
import styles from './SchedulePage.module.css';
import { cn } from '@shared/lib/utils';

const RU_MONTHS: Record<number, string> = {
  0: 'Январь', 1: 'Февраль', 2: 'Март', 3: 'Апрель',
  4: 'Май', 5: 'Июнь', 6: 'Июль', 7: 'Август',
  8: 'Сентябрь', 9: 'Октябрь', 10: 'Ноябрь', 11: 'Декабрь',
};
const RU_MONTHS_GEN: Record<number, string> = {
  0: 'января', 1: 'февраля', 2: 'марта', 3: 'апреля',
  4: 'мая', 5: 'июня', 6: 'июля', 7: 'августа',
  8: 'сентября', 9: 'октября', 10: 'ноября', 11: 'декабря',
};
const RU_DAYS_SHORT = ['ВС', 'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ'];

function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function addDays(date: Date, n: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}T00:00:00`;
}

function toISODateEnd(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}T23:59:59`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getDate()} ${RU_MONTHS_GEN[d.getMonth()]} ${d.getFullYear()}, ${formatTime(iso)}`;
}

function homeworkActionLabel(s: HomeworkScheduleItem['attempt_status']): string {
  if (s === 'not_started') return 'Начать';
  if (s === 'draft') return 'Продолжить';
  if (s === 'submitted') return 'На проверке';
  if (s === 'reviewed') return 'Посмотреть оценку';
  return 'Перейти';
}

interface PopupState {
  item: ScheduleItem;
}

function WebinarPopup({ item, onClose }: { item: WebinarScheduleItem; onClose: () => void }) {
  const navigate = useNavigate();
  const lessonUrl = `/app/courses/${item.course_slug}/${item.lesson_slug}`;

  return (
    <div className={styles.popupInner}>
      <div className={styles.popupHeader}>
        <div className={styles.popupMeta}>
          <Video size={14} className={styles.popupIconWebinar} />
          <span className={styles.popupTypeWebinar}>Вебинар</span>
        </div>
        <button type="button" className={styles.popupClose} onClick={onClose}><X size={14} /></button>
      </div>
      <div className={styles.popupTitle}>{item.title}</div>
      <div className={styles.popupCourse}>{item.course_title}</div>
      <div className={styles.popupDateRow}>
        <Clock size={13} className={styles.popupDateIcon} />
        <span>{formatDateTime(item.scheduled_at ?? item.datetime)}</span>
      </div>
      <div className={styles.popupActions}>
        {item.webinar_status === 'pending' && (
          <Button type="button" variant="outline" disabled>Ещё не начался</Button>
        )}
        {item.webinar_status === 'live' && (
          <Button type="button" className={styles.popupBtnWebinar} onClick={() => navigate(lessonUrl)}>Подключиться</Button>
        )}
        {item.webinar_status === 'ended' && (
          <Button type="button" className={styles.popupBtnWebinar} onClick={() => navigate(lessonUrl)}>Перейти к записи</Button>
        )}
      </div>
    </div>
  );
}

function HomeworkPopup({ item, onClose }: { item: HomeworkScheduleItem; onClose: () => void }) {
  const navigate = useNavigate();
  const hwUrl = `/app/courses/${item.course_slug}/${item.homework_lesson_slug}/homeworks/${item.homework_slug}`;
  const isSubmitted = item.attempt_status === 'submitted';

  return (
    <div className={styles.popupInner}>
      <div className={styles.popupHeader}>
        <div className={styles.popupMeta}>
          <Clock size={14} className={styles.popupIconHomework} />
          <span className={styles.popupTypeHomework}>Домашнее задание</span>
        </div>
        <button type="button" className={styles.popupClose} onClick={onClose}><X size={14} /></button>
      </div>
      <div className={styles.popupTitle}>{item.title}</div>
      <div className={styles.popupCourse}>{item.course_title}</div>
      <div className={styles.popupDateRow}>
        <Clock size={13} className={styles.popupDateIcon} />
        <span>Дедлайн: {formatDateTime(item.deadline)}</span>
      </div>
      <div className={styles.popupActions}>
        <Button
          type="button"
          className={!isSubmitted ? styles.popupBtnHomework : undefined}
          variant={isSubmitted ? 'outline' : 'primary'}
          disabled={isSubmitted}
          onClick={() => { if (!isSubmitted) navigate(hwUrl); }}
        >
          {homeworkActionLabel(item.attempt_status)}
        </Button>
      </div>
    </div>
  );
}

function EventCard({ item, onOpen }: { item: ScheduleItem; onOpen: (e: React.MouseEvent<HTMLDivElement>) => void }) {
  const isWebinar = item.type === 'webinar';
  return (
    <div
      role="button"
      tabIndex={0}
      className={isWebinar ? styles.cardWebinar : styles.cardHomework}
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }}
    >
      <div className={styles.cardHeader}>
        {isWebinar
          ? <Video size={15} className={styles.cardIconWebinar} />
          : <Clock size={15} className={styles.cardIconHomework} />}
        <div className={styles.cardHeaderMeta}>
          <span className={cn(styles.cardTime, isWebinar ? styles.cardTypeWebinar : styles.cardTypeHomework)}>
            {formatTime(item.datetime)}
          </span>
          <span className={isWebinar ? styles.cardTypeWebinar : styles.cardTypeHomework}>
            {isWebinar ? 'Вебинар' : 'ДД задания'}
          </span>
        </div>
      </div>
      <div className={styles.cardTitle}>{item.title}</div>
      <div className={styles.cardCourse}>{item.course_title}</div>
    </div>
  );
}

interface LoadedRange { start: Date; end: Date; }

export default function SchedulePage() {
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const thisWeekMonday = useMemo(() => startOfWeek(today), [today]);
  const [weekStart, setWeekStart] = useState<Date>(() => {
    const saved = sessionStorage.getItem('schedule_week');
    if (saved) {
      const d = new Date(saved);
      if (!isNaN(d.getTime())) return d;
    }
    return thisWeekMonday;
  });
  const [loadedRange, setLoadedRange] = useState<LoadedRange>(() => {
    const saved = sessionStorage.getItem('schedule_week');
    const base = saved ? (() => { const d = new Date(saved); return isNaN(d.getTime()) ? thisWeekMonday : d; })() : thisWeekMonday;
    return {
      start: addDays(base, -7),
      end: addDays(base, 3 * 7 - 1),
    };
  });

  const { data, isFetching } = useSchedule(toISODate(loadedRange.start), toISODateEnd(loadedRange.end));

  const [accumulated, setAccumulated] = useState<Map<string, ScheduleItem>>(new Map());
  useEffect(() => {
    if (!data) return;
    setAccumulated((prev) => {
      const next = new Map(prev);
      for (const item of data.items) {
        const key = item.type === 'webinar' ? `w::${item.webinar_id}` : `h::${item.homework_id}`;
        next.set(key, item);
      }
      return next;
    });
  }, [data]);

  const allItems = useMemo(() => Array.from(accumulated.values()), [accumulated]);
  const weekEnd = addDays(weekStart, 6);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  const itemsByDay = useMemo(() => {
    const map = new Map<string, ScheduleItem[]>();
    for (const day of weekDays) map.set(day.toDateString(), []);
    for (const item of allItems) {
      const key = new Date(item.datetime).toDateString();
      if (map.has(key)) map.get(key)!.push(item);
    }
    return map;
  }, [allItems, weekDays]);

  const [popup, setPopup] = useState<PopupState | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  function openPopup(item: ScheduleItem) {
    setPopup({ item });
  }

  function goNext() {
    setWeekStart((w) => {
      const next = addDays(w, 7);
      sessionStorage.setItem('schedule_week', next.toISOString());
      setLoadedRange((r) => {
        if (addDays(next, 6).getTime() >= addDays(r.end, -7).getTime()) {
          return { ...r, end: addDays(r.end, 4 * 7) };
        }
        return r;
      });
      return next;
    });
  }

  function goPrev() {
    setWeekStart((w) => {
      const prev = addDays(w, -7);
      sessionStorage.setItem('schedule_week', prev.toISOString());
      setLoadedRange((r) => {
        if (prev.getTime() <= addDays(r.start, 7).getTime()) {
          return { ...r, start: addDays(r.start, -2 * 7) };
        }
        return r;
      });
      return prev;
    });
  }

  const monthLabel = (() => {
    const sm = RU_MONTHS[weekStart.getMonth()];
    const em = weekEnd.getMonth() !== weekStart.getMonth() ? ` / ${RU_MONTHS[weekEnd.getMonth()]}` : '';
    return `${sm}${em} ${weekStart.getFullYear()}`;
  })();

  const rangeLabel = `${weekStart.getDate()} ${RU_MONTHS_GEN[weekStart.getMonth()]} — ${weekEnd.getDate()} ${RU_MONTHS_GEN[weekEnd.getMonth()]}`;

  return (
    <PageFrame>
      <div className={styles.page}>
        <div className={styles.wrap}>
          <div className={styles.header}>
            <button type="button" className={styles.navArrow} onClick={goPrev}>‹</button>
            <div className={styles.headerTitle}>
              <span className={styles.monthLabel}>{monthLabel}</span>
              <span className={styles.rangeLabel}>{rangeLabel}</span>
            </div>
            <button type="button" className={styles.navArrow} onClick={goNext}>›</button>
          </div>

          <div className={styles.grid}>
            {weekDays.map((day) => {
              const isToday = isSameDay(day, today);
              return (
                <div key={day.toDateString()} className={styles.dayHeader}>
                  <span className={styles.dayName}>{RU_DAYS_SHORT[day.getDay()]}</span>
                  <span className={isToday ? styles.dayNumToday : styles.dayNum}>{day.getDate()}</span>
                </div>
              );
            })}
            {weekDays.map((day) => {
              const isToday = isSameDay(day, today);
              const dayItems = itemsByDay.get(day.toDateString()) ?? [];
              return (
                <div key={`col-${day.toDateString()}`} className={[styles.dayCol, isToday ? styles.dayColToday : ''].join(' ')}>
                  {dayItems.length === 0 && isFetching
                    ? (isToday ? <div className={styles.colSpinner}><Spinner size="sm" /></div> : null)
                    : dayItems.map((item) => (
                      <EventCard
                        key={item.type === 'webinar' ? item.webinar_id : item.homework_id}
                        item={item}
                        onOpen={() => openPopup(item)}
                      />
                    ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {popup && (
        <div className={styles.overlay} onMouseDown={() => setPopup(null)}>
          <div
            ref={popupRef}
            className={styles.popup}
            onMouseDown={(e) => e.stopPropagation()}
          >
            {popup.item.type === 'webinar'
              ? <WebinarPopup item={popup.item} onClose={() => setPopup(null)} />
              : <HomeworkPopup item={popup.item} onClose={() => setPopup(null)} />}
          </div>
        </div>
      )}
    </PageFrame>
  );
}
