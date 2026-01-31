import RegistrationForm from './RegistrationForm';
import styles from './RegistrationPage.module.css';

export default function RegistrationPage() {
  return (
    <div className={styles.container}>
      <div className={styles.wrapper}>
        <RegistrationForm />
      </div>
    </div>
  );
}
