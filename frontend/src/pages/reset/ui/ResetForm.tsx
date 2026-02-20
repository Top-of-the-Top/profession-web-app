import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import { useState } from 'react';
import { Field, FieldGroup, FieldLabel, Input } from '../../../shared/ui';
import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import styles from './ResetPage.module.css';
import { Link, useNavigate } from 'react-router-dom';
import { resetUser } from '../api';
import { validateEmailOrPhone } from '../../../shared/utils/validation';
import toast, { Toaster } from 'react-hot-toast';

export default function ResetForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const emailOrPhone = (form.elements.namedItem('email') as HTMLInputElement)
      .value;

    const validation = validateEmailOrPhone(emailOrPhone);

    if (!validation.isValid) {
      toast.error('Введите корректный email или номер телефона');
      setLoading(false);
      return;
    }

    try {
      await resetUser({ emailOrPhone });

      toast.success(
        'Ссылка для сброса пароля отправлена на вашу почту или телефон',
        {
          duration: 5000,
          icon: <CheckCircle2 className={styles.toastSuccessIcon} />,
        }
      );

      setSuccess(true);
    } catch (err: any) {
      if (err.response?.status === 400) {
        toast.error('Некорректные данные. Проверьте введенные данные');
      } else if (err.response?.status === 404) {
        toast.error('Пользователь с такими данными не найден');
      } else if (err.response?.status === 429) {
        toast.error('Слишком много попыток. Попробуйте позже');
      } else if (err.response?.status === 500) {
        toast.error('Сервер временно недоступен. Попробуйте позже');
      } else {
        toast.error(err.message || 'Произошла ошибка при отправке запроса');
      }
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
                      name="email"
                      type="text"
                      placeholder="Почта/телефон"
                      autoComplete="email"
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                    <CardDescription
                      style={{ fontSize: '12px', marginTop: '4px' }}
                    >
                      Например: example@email.com или +79991234567
                    </CardDescription>
                  </Field>

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

      <Toaster
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
            borderRadius: '8px',
            fontSize: '14px',
          },
          success: {
            duration: 5000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  );
}
