import { useEffect } from 'react';
import RegistrationForm from './RegistrationForm';
import styles from './RegistrationPage.module.css';
import { preloadAppCore } from '../../../router/lazyPages';

export default function RegistrationPage() {
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
        <RegistrationForm />
      </div>
    </div>
  );
}
