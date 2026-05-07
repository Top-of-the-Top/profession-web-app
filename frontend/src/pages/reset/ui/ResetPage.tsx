import { lazy, Suspense } from 'react';
import styles from './ResetPage.module.css';
import { Spinner } from '@shared/ui';

const ResetForm = lazy(() => import('./ResetForm'));

export default function ResetPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={<Spinner size="lg" />}>
          <ResetForm />
        </Suspense>
      </div>
    </div>
  );
}
