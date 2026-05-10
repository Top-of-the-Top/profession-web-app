import { useRouteError, isRouteErrorResponse, useNavigate } from 'react-router-dom';
import styles from './RootErrorFallback.module.css';

const isDev = import.meta.env.DEV;

export function RouterErrorFallback() {
  const error = useRouteError();
  const navigate = useNavigate();

  const is404 = isRouteErrorResponse(error) && error.status === 404;

  const message = isRouteErrorResponse(error)
    ? error.statusText
    : error instanceof Error
      ? error.message
      : 'Неизвестная ошибка';

  const stack = error instanceof Error ? error.stack : undefined;

  if (is404) {
    return (
      <div className={styles.root}>
        <div className={styles.container}>
          <span className={styles.code}>404</span>
          <div className={styles.message}>
            <h1>Страница не найдена</h1>
            <p>Такой страницы не существует.</p>
          </div>
          <button className={styles.btn} onClick={() => navigate('/')}>
            На главную
          </button>
        </div>
        <span className={styles.codeHint}>error_code: 404</span>
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <div className={styles.container}>
        <span className={styles.code}>500</span>
        <div className={styles.message}>
          <h1>Что-то пошло не так</h1>
          <p>Произошла непредвиденная ошибка. Попробуйте перезагрузить страницу.</p>
        </div>
        <button className={styles.btn} onClick={() => window.location.reload()}>
          Перезагрузить
        </button>
        {isDev && (
          <details className={styles.devDetails}>
            <summary className={styles.devSummary}>{message}</summary>
            {stack && <pre className={styles.devPre}>{stack}</pre>}
          </details>
        )}
      </div>
      <span className={styles.codeHint}>error_code: 500</span>
    </div>
  );
}
