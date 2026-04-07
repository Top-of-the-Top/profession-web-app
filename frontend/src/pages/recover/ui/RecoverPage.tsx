import { lazy, Suspense, useLayoutEffect } from 'react';
import styles from './RecoverPage.module.css';
import { preloadAppCore } from '@router/lazyPages';

const RecoverForm = lazy(() => import('./RecoverForm'));

export default function RecoverPage() {
  useLayoutEffect(() => {
    preloadAppCore();
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={null}>
          <RecoverForm />
        </Suspense>
      </div>
    </div>
  );
}
