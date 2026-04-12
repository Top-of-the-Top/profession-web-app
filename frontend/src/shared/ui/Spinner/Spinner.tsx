import { cn } from '@shared/lib/utils';
import styles from './Spinner.module.css';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  full?: boolean;
  className?: string;
}

export function Spinner({ size = 'md', full = false, className }: SpinnerProps) {
  return (
    <div
      className={cn(
        full ? styles.wrapperFull : styles.wrapper,
        size !== 'md' && styles[size],
        className,
      )}
    >
      <div className={styles.dots}>
        <div className={styles.dot} />
        <div className={styles.dot} />
        <div className={styles.dot} />
      </div>
    </div>
  );
}
