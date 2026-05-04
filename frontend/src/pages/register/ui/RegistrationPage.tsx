import { lazy, Suspense } from 'react';
import styles from './RegistrationPage.module.css';
import { Spinner } from '@shared/ui';

const RegistrationForm = lazy(() => import('./RegistrationForm'));

export default function RegistrationPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={<Spinner size="lg" />}>
          <RegistrationForm />
        </Suspense>
      </div>
    </div>
  );
}
