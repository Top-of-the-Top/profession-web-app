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
import { ArrowLeft } from 'lucide-react';
import styles from './ResetPage.module.css';
import { Link, useNavigate } from 'react-router-dom';
import { resetUser } from '../api';
import { validateEmailOrPhone } from '../../../shared/utils/validation';
import { ZodError } from 'zod';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifySuccess,
} from '../../../shared/lib/sileo/notify';

function notifyResetFailure(err: unknown) {
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('resetRequest', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure('resetRequest', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

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
      notifyError({
        title: 'проверьте контакт',
        description: 'Введите корректный email или номер телефона.',
      });
      setLoading(false);
      return;
    }

    try {
      await resetUser({ emailOrPhone });
      notifySuccess({
        title: 'ссылка отправлена',
        description: 'Проверьте почту или SMS — там будет ссылка для сброса пароля.',
      });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ZodError) {
        notifyError({
          title: 'некорректный ответ сервера',
          description: 'Обновите страницу или попробуйте позже.',
        });
        return;
      }
      notifyResetFailure(err);
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
    </div>
  );
}
