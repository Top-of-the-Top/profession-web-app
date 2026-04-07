import { Button } from '@shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@shared/ui';
import { useState } from 'react';
import { Field, FieldGroup, FieldLabel, Input } from '@shared/ui';
import { ArrowLeft } from 'lucide-react';
import styles from './ResetPage.module.css';
import { Link, useNavigate } from 'react-router-dom';
import { resetUser } from '../api';
import { validateEmailOrPhone } from '@shared/utils/validation';
import { ZodError } from 'zod';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifySuccess,
} from '@shared/lib/sileo/notify';
import { verifyRecoverPhoneCode } from '@pages/recover/api';

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

function notifyRecoverPhoneFailure(err: unknown) {
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('recoverPhone', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure('recoverPhone', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

type Phase = 'request' | 'emailSent' | 'phoneCode';

export default function ResetForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<Phase>('request');
  const [normalizedPhone, setNormalizedPhone] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleRequestSubmit = async (e: React.FormEvent) => {
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
      const res = await resetUser({ emailOrPhone });
      if (validation.isEmail) {
        notifySuccess({
          title: 'письмо отправлено',
          description:
            res.detail ??
            'Проверьте почту — там будет ссылка для сброса пароля.',
        });
        setPhase('emailSent');
      } else {
        notifySuccess({
          title: 'SMS отправлено',
          description:
            res.detail ??
            'Код для сброса пароля отправлен на телефон.',
        });
        setNormalizedPhone(validation.normalized);
        setPhase('phoneCode');
      }
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

  const handlePhoneCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!normalizedPhone) return;
    setLoading(true);
    const form = e.currentTarget as HTMLFormElement;
    const codeRaw = (form.elements.namedItem('code') as HTMLInputElement).value;
    const code = codeRaw.replace(/\D/g, '');
    if (code.length !== 6) {
      notifyError({
        title: 'неверный код',
        description: 'Введите 6 цифр из SMS.',
      });
      setLoading(false);
      return;
    }
    try {
      const { token } = await verifyRecoverPhoneCode({
        phone_number: normalizedPhone,
        code,
      });
      navigate(
        `/recover?token=${encodeURIComponent(token)}&channel=phone`,
      );
    } catch (err) {
      if (err instanceof ZodError) {
        notifyError({
          title: 'некорректный ответ сервера',
          description: 'Обновите страницу или попробуйте позже.',
        });
        return;
      }
      notifyRecoverPhoneFailure(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="landing/profession-logo-blue.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>
              Сброс пароля
            </CardTitle>
            <CardDescription>
              {phase === 'request' &&
                'Введите адрес электронной почты или номер телефона.'}
              {phase === 'emailSent' &&
                'Ссылка для сброса пароля отправлена на вашу почту.'}
              {phase === 'phoneCode' &&
                'Введите 6-значный код из SMS, затем задайте новый пароль.'}
            </CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            {phase === 'emailSent' ? (
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
            ) : phase === 'phoneCode' ? (
              <form onSubmit={handlePhoneCodeSubmit}>
                <FieldGroup className={styles.fieldGroup}>
                  <Field className={styles.field}>
                    <FieldLabel htmlFor="code">Код из SMS</FieldLabel>
                    <Input
                      id="code"
                      name="code"
                      type="text"
                      inputMode="numeric"
                      placeholder="••••••"
                      maxLength={6}
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                  </Field>
                  <Button
                    style={{ fontSize: '14px' }}
                    type="submit"
                    className={styles.submitButton}
                    disabled={loading}
                  >
                    {loading ? 'Проверка...' : 'Продолжить'}
                  </Button>
                  <div className={styles.linksContainer}>
                    <div className={styles.linkRow}>
                      <button
                        type="button"
                        className={styles.link}
                        onClick={() => {
                          setPhase('request');
                          setNormalizedPhone(null);
                        }}
                      >
                        <ArrowLeft size={20} /> Назад
                      </button>
                    </div>
                  </div>
                </FieldGroup>
              </form>
            ) : (
              <form onSubmit={handleRequestSubmit}>
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
                    {loading ? 'Отправка...' : 'Отправить'}
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
