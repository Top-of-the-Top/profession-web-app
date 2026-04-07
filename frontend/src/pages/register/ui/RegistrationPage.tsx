import { lazy, Suspense, useLayoutEffect } from 'react';
import styles from './RegistrationPage.module.css';
import { preloadAppCore } from '@router/lazyPages';

const RegistrationForm = lazy(() => import('./RegistrationForm'));

export default function RegistrationPage() {
  useLayoutEffect(() => {
    preloadAppCore();
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={null}>
          <RegistrationForm />
        </Suspense>
      </div>
    </div>
  );
}
