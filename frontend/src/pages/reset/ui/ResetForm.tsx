import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import { useState } from 'react';

import {
  Field,
  FieldGroup,
  FieldLabel,
} from '../../../shared/ui';

import { ArrowLeft } from 'lucide-react';
import Input from '../../../shared/ui/Input/Input';
import styles from './ResetPage.module.css';
import { Link, useNavigate } from 'react-router-dom';
import { resetUser } from '../api';

export default function ResetForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const emailOrPhone = (form.elements.namedItem('email') as HTMLInputElement)
      .value;

    try {
      await resetUser({ emailOrPhone });
      setSuccess(true);
      
    } catch (err: any) {
      setError(err.message || 'Произошла ошибка при отправке запроса');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="landing/profession-logo.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>
              Сброс пароля
            </CardTitle>
            <CardDescription>
              {success
                ? 'Ссылка для сброса пароля отправлена на вашу почту или телефон'
                : 'Введите свой адрес электронной почты или номер телефона, и мы вышлем вам ссылку для сброса вашего пароля'}
            </CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            {success ? (
              <div className={styles.successMessage}>
                
                {/* <p style={{ textAlign: 'center', fontSize: '14px', color: '#666' }}>
                  Проверьте вашу почту или телефон для получения инструкций по сбросу пароля.
                </p> */}
                <Button
                  style={{ fontSize: '14px', marginTop: '20px' }}
                  type="button"
                  className={styles.submitButton}
                  onClick={() => navigate('/login')}
                >
                  Вернуться ко входу
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <FieldGroup className={styles.fieldGroup}>
                  <Field className={styles.field}>
                    <FieldLabel htmlFor="email">
                      Почта или номер телефона
                    </FieldLabel>
                    <Input
                      id="email"
                      type="text"
                      placeholder="Почта/телефон"
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                  </Field>

                  {error && (
                    <div className={styles.errorMessage}>
                      {error}
                    </div>
                  )}

                  <Button
                    style={{ fontSize: '14px' }}
                    type="submit"
                    className={styles.submitButton}
                    disabled={loading}
                  >
                    {loading ? 'Отправка...' : 'Отправить ссылку'}
                  </Button>

                  <div className={styles.linksContainer}>
                    <div className={styles.linkRow}>
                      <Link to="/login" className={styles.link}>
                        <ArrowLeft size={20} /> Обратно ко входу
                      </Link>
                    </div>
                  </div>
                </FieldGroup>
              </form>
            )}
          </CardContent>
        </Card>
        <div className={styles.copyright}>&copy; 2026 Профессия</div>
      </div>
    </div>
  );
}