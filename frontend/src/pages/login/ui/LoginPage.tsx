import { lazy, Suspense, useLayoutEffect } from 'react';
import styles from './LoginPage.module.css';
import { preloadAppCore } from '@router/lazyPages';

const LoginForm = lazy(() => import('./LoginForm'));

export default function LoginPage() {
  useLayoutEffect(() => {
    preloadAppCore();
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
