import { lazy, Suspense } from 'react';
import styles from './LoginPage.module.css';
import { Spinner } from '@shared/ui';

const LoginForm = lazy(() => import('./LoginForm'));

export default function LoginPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={<Spinner size="lg" />}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
