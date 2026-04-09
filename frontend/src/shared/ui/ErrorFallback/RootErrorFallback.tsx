import type { FallbackProps } from 'react-error-boundary';
import styles from './RootErrorFallback.module.css';

const isDev = import.meta.env.DEV;

export function RootErrorFallback({ error }: FallbackProps) {
  const message =
    error instanceof Error ? error.message : 'Неизвестная ошибка';
  const stack = error instanceof Error ? error.stack : undefined;

  return (
    <div className={styles.root}>
      <div className={styles.container}>
        <span className={styles.code}>500</span>

        <div className={styles.message}>
          <h1>Что-то пошло не так</h1>
          <p>Произошла непредвиденная ошибка. Попробуйте перезагрузить страницу.</p>
        </div>

        <button
          className={styles.btn}
          onClick={() => window.location.reload()}
        >
          Перезагрузить
        </button>

        {isDev && (
          <details className={styles.devDetails}>
            <summary className={styles.devSummary}>
              {message}
            </summary>
            {stack && <pre className={styles.devPre}>{stack}</pre>}
          </details>
        )}
      </div>

      <span className={styles.codeHint}>error_code: 500</span>
    </div>
  );
}
