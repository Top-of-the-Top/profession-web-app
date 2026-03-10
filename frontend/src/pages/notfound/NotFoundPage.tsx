import { useRef } from 'react';
import { Link } from 'react-router-dom';
import styles from './NotFoundPage.module.css';

export default function NotFoundPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  return (
    <div className={styles.root}>
      <div className={styles.container}>
        <div className={styles.errorRow}>
          <span className={styles.digit}>4</span>

          <div className={styles.videoZero}>
            <video
              ref={videoRef}
              src="/media/head.mp4"
              autoPlay
              loop
              muted
              playsInline
              onError={(e) => {
                const video = e.currentTarget;
                video.style.display = 'none';
                const placeholder = video.nextElementSibling as HTMLElement | null;
                if (placeholder) placeholder.style.display = 'flex';
              }}
            />

            <div className={styles.placeholder}>
              Видео не загрузилось
            </div>
          </div>

          <span className={styles.digit}>4</span>
        </div>

        <div className={styles.message}>
          <h1>Страница не найдена</h1>
          <p>Возможно, она переехала или никогда не существовала.</p>
        </div>

        <Link className={styles.btn} to="/">
          На главную
        </Link>
      </div>

      <span className={styles.codeHint}>error_code: 404</span>
    </div>
  );
}