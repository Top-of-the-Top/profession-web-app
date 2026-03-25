import { useLocation, useNavigate } from 'react-router-dom';
import { CourseRenderer } from '../../../features/course-builder';
import type { CoursePage } from '../../../features/course-builder';
import styles from './LessonPreviewPage.module.css';

export default function LessonPreviewPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const data = location.state as CoursePage | undefined;

  if (!data) {
    return (
      <div className={styles.emptyState}>
        <p>Нет данных для предпросмотра.</p>
        <button
          type="button"
          className={styles.backButton}
          onClick={() => navigate(-1)}
        >
          Вернуться
        </button>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.previewBanner}>
        <span className={styles.previewLabel}>Предпросмотр урока</span>
        <button
          type="button"
          className={styles.backButton}
          onClick={() => navigate(-1)}
        >
          Назад к редактору
        </button>
      </header>
      <CourseRenderer data={data} />
    </div>
  );
}
