import { lazy, Suspense, useLayoutEffect } from 'react';
import styles from './ResetPage.module.css';
import { preloadAppCore } from '@router/lazyPages';

const ResetForm = lazy(() => import('./ResetForm'));

export default function ResetPage() {
  useLayoutEffect(() => {
    preloadAppCore();
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={null}>
          <ResetForm />
        </Suspense>
      </div>
    </div>
  );
}
