import RecoverForm from './RecoverForm';
import styles from './RecoverPage.module.css';

export default function RecoverPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <RecoverForm />
      </div>
    </div>
  );
}
