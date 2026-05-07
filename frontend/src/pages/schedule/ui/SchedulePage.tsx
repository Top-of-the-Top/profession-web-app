import { useEffect, useMemo, useRef, useState } from 'react';
import { Video, Clock } from 'lucide-react';
import { PageFrame, Spinner } from '@shared/ui';
import { useSchedule } from '@shared/api/queries/schedule';
import type { ScheduleItem } from '@shared/api/scheduleApi';
import styles from './SchedulePage.module.css';

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

interface LoadedRange {
  start: Date; // monday of earliest loaded week
  end: Date;   // sunday of latest loaded week
}

function EventCard({ item }: { item: ScheduleItem }) {
  const isWebinar = item.type === 'webinar';
  return (
    <div className={isWebinar ? styles.cardWebinar : styles.cardHomework}>
      <div className={styles.cardHeader}>
        {isWebinar ? (
          <Video size={15} className={styles.cardIconWebinar} />
        ) : (
          <Clock size={15} className={styles.cardIconHomework} />
        )}
        <div className={styles.cardHeaderMeta}>
          <span className={styles.cardTime}>{formatTime(item.datetime)}</span>
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

export default function SchedulePage() {
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const thisWeekMonday = useMemo(() => startOfWeek(today), [today]);

  // Current displayed week
  const [weekStart, setWeekStart] = useState<Date>(() => thisWeekMonday);

  // Loaded range: initially [-1w, +2w] = 4 weeks
  const [loadedRange, setLoadedRange] = useState<LoadedRange>(() => ({
    start: addDays(thisWeekMonday, -7),
    end: addDays(thisWeekMonday, 3 * 7 - 1), // +2w sunday
  }));

  const rangeStartIso = toISODate(loadedRange.start);
  const rangeEndIso = toISODateEnd(loadedRange.end);

  const { data, isFetching } = useSchedule(rangeStartIso, rangeEndIso);

  // Accumulate all ever-fetched items across range expansions so switching
  // weeks that are already in cache never shows empty columns mid-fetch.
  const accumulatedRef = useRef<Map<string, ScheduleItem>>(new Map());
  useEffect(() => {
    if (!data) return;
    for (const item of data.items) {
      const key = `${item.datetime}::${item.title}`;
      accumulatedRef.current.set(key, item);
    }
  }, [data]);

  const allItems = useMemo(() => {
    // Rebuild when data changes; snapshot the ref value.
    return Array.from(accumulatedRef.current.values());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const weekEnd = addDays(weekStart, 6);

  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  const itemsByDay = useMemo(() => {
    const map = new Map<string, ScheduleItem[]>();
    for (const day of weekDays) {
      map.set(day.toDateString(), []);
    }
    for (const item of allItems) {
      const d = new Date(item.datetime);
      const key = d.toDateString();
      if (map.has(key)) {
        map.get(key)!.push(item);
      }
    }
    return map;
  }, [allItems, weekDays]);

  function goNext() {
    setWeekStart((w) => {
      const next = addDays(w, 7);
      const nextEnd = addDays(next, 6);
      // If the new week's end would be within 1 week of loadedRange.end → extend by 4 weeks
      setLoadedRange((r) => {
        if (nextEnd.getTime() >= addDays(r.end, -7).getTime()) {
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
      // If the new week's start would be within 1 week of loadedRange.start → extend by 2 weeks
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
    const startMonth = RU_MONTHS[weekStart.getMonth()];
    const endMonth = weekEnd.getMonth() !== weekStart.getMonth()
      ? ` / ${RU_MONTHS[weekEnd.getMonth()]}`
      : '';
    const year = weekStart.getFullYear();
    return `${startMonth}${endMonth} ${year}`;
  })();

  const rangeLabel = (() => {
    const s = `${weekStart.getDate()} ${RU_MONTHS_GEN[weekStart.getMonth()]}`;
    const e = `${weekEnd.getDate()} ${RU_MONTHS_GEN[weekEnd.getMonth()]}`;
    return `${s} - ${e}`;
  })();

  return (
    <PageFrame>
      <div className={styles.page}>
        <div className={styles.wrap}>
          <div className={styles.header}>
            <button type="button" className={styles.navArrow} onClick={goPrev}>
              ‹
            </button>
            <div className={styles.headerTitle}>
              <span className={styles.monthLabel}>{monthLabel}</span>
              <span className={styles.rangeLabel}>{rangeLabel}</span>
            </div>
            <button type="button" className={styles.navArrow} onClick={goNext}>
              ›
            </button>
          </div>

          <div className={styles.grid}>
            {weekDays.map((day) => {
              const isToday = isSameDay(day, today);
              return (
                <div key={day.toDateString()} className={styles.dayHeader}>
                  <span className={styles.dayName}>
                    {RU_DAYS_SHORT[day.getDay()]}
                  </span>
                  <span className={isToday ? styles.dayNumToday : styles.dayNum}>
                    {day.getDate()}
                  </span>
                </div>
              );
            })}

            {weekDays.map((day) => {
              const isToday = isSameDay(day, today);
              const dayItems = itemsByDay.get(day.toDateString()) ?? [];
              return (
                <div
                  key={`col-${day.toDateString()}`}
                  className={[styles.dayCol, isToday ? styles.dayColToday : ''].join(' ')}
                >
                  {dayItems.length === 0 && isFetching ? (
                    isToday ? <div className={styles.colSpinner}><Spinner size="sm" /></div> : null
                  ) : (
                    dayItems.map((item, idx) => (
                      <EventCard key={`${item.datetime}-${idx}`} item={item} />
                    ))
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </PageFrame>
  );
}
