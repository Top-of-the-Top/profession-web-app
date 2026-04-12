import { Link } from 'react-router-dom';
import styles from './NotAuthorizedPage.module.css';

export default function NotAuthorizedPage() {
  return (
    <div className={styles.root}>
      <div className={styles.container}>
        <span className={styles.code}>403</span>

        <div className={styles.message}>
          <h1>Доступ запрещён</h1>
          <p>У вас нет прав для просмотра этой страницы.</p>
        </div>

        <Link className={styles.btn} to="/app/home">
          На главную
        </Link>
      </div>

      <span className={styles.codeHint}>error_code: 403</span>
    </div>
  );
}
