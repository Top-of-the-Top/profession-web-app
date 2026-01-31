import ResetForm from './ResetForm';
import styles from './ResetPage.module.css';

export default function RecoverPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <ResetForm />
      </div>
    </div>
  );
}
