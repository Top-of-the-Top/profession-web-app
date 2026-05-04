import { Check } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import styles from '../CourseLessonsPage.module.css';

export function StudentStatusIcon({ done }: { done: boolean }) {
  if (done) {
    return (
      <span
        className={cn(styles.statusIcon, styles.statusIconDone)}
        aria-hidden
      >
        <Check size={14} strokeWidth={3} />
      </span>
    );
  }

  return (
    <span
      className={cn(styles.statusIcon, styles.statusIconPending)}
      aria-hidden
    >
      <span className={styles.statusIconPendingBars}>
        <span className={styles.statusIconPendingBar} />
        <span className={styles.statusIconPendingBar} />
      </span>
    </span>
  );
}
