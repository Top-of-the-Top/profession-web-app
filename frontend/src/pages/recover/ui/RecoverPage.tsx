import { lazy, Suspense } from 'react';
import styles from './RecoverPage.module.css';
import { Spinner } from '@shared/ui';

const RecoverForm = lazy(() => import('./RecoverForm'));

export default function RecoverPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={<Spinner size="lg" />}>
          <RecoverForm />
        </Suspense>
      </div>
    </div>
  );
}
