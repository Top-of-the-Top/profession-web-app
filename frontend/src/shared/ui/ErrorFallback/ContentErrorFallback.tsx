import { AlertTriangle } from 'lucide-react';
import type { FallbackProps } from 'react-error-boundary';
import styles from './ContentErrorFallback.module.css';

const isDev = import.meta.env.DEV;

export function ContentErrorFallback({
  error,
  resetErrorBoundary,
}: FallbackProps) {
  const message =
    error instanceof Error ? error.message : 'Неизвестная ошибка';
  const stack = error instanceof Error ? error.stack : undefined;

  return (
    <div className={styles.root}>
      <AlertTriangle className={styles.icon} strokeWidth={1.5} />

      <h2 className={styles.title}>Ошибка загрузки страницы</h2>
      <p className={styles.description}>
        Произошла непредвиденная ошибка при отображении этой страницы
      </p>

      <button className={styles.btn} onClick={resetErrorBoundary}>
        Попробовать снова
      </button>

      {isDev && (
        <details className={styles.devDetails}>
          <summary className={styles.devSummary}>{message}</summary>
          {stack && <pre className={styles.devPre}>{stack}</pre>}
        </details>
      )}
    </div>
  );
}
