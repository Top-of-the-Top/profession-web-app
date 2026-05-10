import type { ReactNode } from 'react';
import { cn } from '@shared/lib/utils';
import styles from './CenteredMessageBlock.module.css';

export type CenteredMessageBlockProps = {
  message: ReactNode;
  title?: ReactNode;
  actions?: ReactNode;
  footnote?: ReactNode;
  className?: string;
};

export function CenteredMessageBlock({
  message,
  title,
  actions,
  footnote,
  className,
}: CenteredMessageBlockProps) {
  return (
    <div className={cn(styles.shell, className)}>
      <div className={styles.inner}>
        {title != null && title !== '' && title !== false && (
          <div className={styles.title}>{title}</div>
        )}
        {typeof message === 'string' || typeof message === 'number' ? (
          <p className={styles.message}>{message}</p>
        ) : (
          <div className={styles.message}>{message}</div>
        )}
        {actions != null ? <div className={styles.actions}>{actions}</div> : null}
        {footnote != null && footnote !== false ? (
          <div className={styles.footnote}>{footnote}</div>
        ) : null}
      </div>
    </div>
  );
}
