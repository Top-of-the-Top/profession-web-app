import { useEffect } from 'react';
import RecoverForm from './RecoverForm';
import styles from './RecoverPage.module.css';
import { preloadAppCore } from '../../../router/lazyPages';

export default function RecoverPage() {
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
        <RecoverForm />
      </div>
    </div>
  );
}
