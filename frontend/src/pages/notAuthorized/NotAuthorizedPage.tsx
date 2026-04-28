import { Link } from 'react-router-dom';
import { PageFrame } from '@shared/ui';
import styles from './NotAuthorizedPage.module.css';

export default function NotAuthorizedPage() {
  return (
    <PageFrame className={styles.shell}>
      <div className={styles.body}>
        <span className={styles.code}>403</span>

        <div className={styles.message}>
          <h1>Доступ запрещён</h1>
          <p>У вас нет прав для просмотра этой страницы.</p>
        </div>

        <Link className={styles.btn} to="/app">
          На главную
        </Link>
      </div>

      <span className={styles.codeHint}>error_code: 403</span>
    </PageFrame>
  );
}
