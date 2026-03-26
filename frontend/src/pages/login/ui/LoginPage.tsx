import { useEffect } from 'react';
import LoginForm from './LoginForm';
import styles from './LoginPage.module.css';
import { preloadAppCore } from '../../../router/lazyPages';

export default function LoginPage() {
  useEffect(() => {
    const id = 'requestIdleCallback' in window
      ? requestIdleCallback(() => preloadAppCore())
      : setTimeout(() => preloadAppCore(), 200);
    return () => {
      if ('requestIdleCallback' in window) cancelIdleCallback(id as number);
      else clearTimeout(id as ReturnType<typeof setTimeout>);
    };
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <LoginForm />
      </div>
    </div>
  );
}
