import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Field,
  FieldGroup,
  FieldLabel,
  Input,
} from '../../../shared/ui';
import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '../../../shared/lib/utils';
import styles from './RegistrationPage.module.css';
import { completeRegisterWithCode, requestRegisterCode } from '../api';
import { Link, useNavigate } from 'react-router-dom';
import { useUserStore } from '../../../entities/user/model/userStore';
import { ZodError } from 'zod';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError, notifySuccess } from '../../../shared/lib/sileo/notify';
import { validateEmailOrPhone } from '../../../shared/utils/validation';

function notifyRegisterFailure(err: unknown) {
  if (
    err instanceof Error &&
    err.message === 'Invalid email or phone number'
  ) {
    notifyError({
      title: 'проверьте контакт',
      description: 'Введите корректный email или номер телефона.',
    });
    return;
  }

  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('register', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }

  const msg = messageForApiFailure('register', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

function formatZodRegisterError(err: ZodError): string {
  const first = err.issues[0];
  if (!first) return 'Обновите страницу или попробуйте позже.';
  const path = first.path.length ? `${first.path.join('.')}: ` : '';
  return `${path}${first.message}`;
}

function notifyRegisterVerifyFailure(err: unknown) {
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('registerVerify', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure('registerVerify', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

type Step = 'credentials' | 'code';

export default function RegistrationForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [step, setStep] = useState<Step>('credentials');
  const [loading, setLoading] = useState(false);
  const [codeSentDetail, setCodeSentDetail] = useState<string | null>(null);
  const [pendingKind, setPendingKind] = useState<'email' | 'phone' | null>(null);
  const [pendingContact, setPendingContact] = useState<string | null>(null);

  const login = useUserStore((s) => s.login);
  const navigate = useNavigate();

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const emailOrPhone = (form.elements.namedItem('email') as HTMLInputElement)
      .value;
    const password = (form.elements.namedItem('password') as HTMLInputElement)
      .value;
    const repeatPassword = (
      form.elements.namedItem('repeatPassword') as HTMLInputElement
    ).value;

    if (password !== repeatPassword) {
      notifyError({
        title: 'пароли не совпадают',
        description: 'Введите одинаковый пароль в оба поля.',
      });
      setLoading(false);
      return;
    }

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
      const res = await requestRegisterCode({ emailOrPhone, password });
      if (res.flow === 'immediate') {
        notifySuccess({
          title: 'аккаунт создан',
          description: 'Сейчас выполняется вход…',
        });
        await login(res.tokens);
        navigate('/app', { replace: true });
        return;
      }
      setCodeSentDetail(res.detail);
      setPendingKind(validation.isEmail ? 'email' : 'phone');
      setPendingContact(validation.normalized);
      setStep('code');
      notifySuccess({
        title: 'код отправлен',
        description: res.detail,
      });
    } catch (err) {
      if (err instanceof ZodError) {
        notifyError({
          title: 'некорректный ответ сервера',
          description: formatZodRegisterError(err),
        });
        return;
      }
      notifyRegisterFailure(err);
    } finally {
      setLoading(false);
    }
  };

   
  const handleCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingKind || !pendingContact) return;

    setLoading(true);
    const form = e.currentTarget as HTMLFormElement;
    const code = (form.elements.namedItem('code') as HTMLInputElement).value.replace(
      /\D/g,
      '',
    );

    if (code.length !== 6) {
      notifyError({
        title: 'неверный код',
        description: 'Введите 6 цифр из письма или SMS.',
      });
      setLoading(false);
      return;
    }

    try {
      const tokens = await completeRegisterWithCode({
        kind: pendingKind,
        normalizedContact: pendingContact,
        code,
      });
      await login(tokens);
      navigate('/app', { replace: true });
    } catch (err) {
      if (err instanceof ZodError) {
        notifyError({
          title: 'некорректный ответ сервера',
          description: formatZodRegisterError(err),
        });
        return;
      }
      notifyRegisterVerifyFailure(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBackToCredentials = () => {
    setStep('credentials');
    setPendingKind(null);
    setPendingContact(null);
    setCodeSentDetail(null);
  };

  return (
    <div className={cn(styles.loginPage, className)} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="profession-logo-blue.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>
              {step === 'credentials' ? 'Создать аккаунт' : 'Подтверждение'}
            </CardTitle>
            <CardDescription>
              {step === 'credentials'
                ? 'Начните работу с Профессией уже сегодня'
                : codeSentDetail ??
                  'Введите код из письма или SMS'}
            </CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            {step === 'credentials' ? (
              <form onSubmit={handleCredentialsSubmit}>
                <FieldGroup className={styles.fieldGroup}>
                  <Field className={styles.field}>
                    <FieldLabel htmlFor="email">
                      Почта или номер телефона
                    </FieldLabel>
                    <Input
                      id="email"
                      type="text"
                      autoComplete="email"
                      placeholder="Почта/телефон"
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                  </Field>

                  <Field className={styles.field}>
                    <div className={styles.passwordHeader}>
                      <FieldLabel htmlFor="password">Пароль</FieldLabel>
                    </div>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="new-password"
                      placeholder="Пароль"
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                    <CardDescription>
                      Не меньше 8 символов
                    </CardDescription>
                  </Field>

                  <Field className={styles.field}>
                    <div className={styles.passwordHeader}>
                      <FieldLabel htmlFor="repeatPassword">
                        Повторите пароль
                      </FieldLabel>
                    </div>
                    <Input
                      id="repeatPassword"
                      type="password"
                      placeholder="Пароль"
                      autoComplete="new-password"
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                  </Field>

                  <Field>
                    <Button
                      style={{ fontSize: '14px' }}
                      type="submit"
                      className={styles.submitButton}
                      disabled={loading}
                    >
                      Получить код <ArrowRight />
                    </Button>

                    <div className={styles.divider}>
                      <span>или</span>
                    </div>

                    <div className={styles.socialButtons}>
                      <Button
                        variant="outline"
                        type="button"
                        className={cn(styles.socialButton, styles.loginVk)}
                      >
                        <span className={styles.socialIcon}>
                          <img src="login/vk.svg" alt="" />
                        </span>
                        Войти с VK ID
                      </Button>
                      <Button
                        variant="outline"
                        type="button"
                        className={cn(styles.socialButton, styles.loginYa)}
                      >
                        <span className={styles.socialIcon}>
                          <img src="login/ya.svg" alt="" />
                        </span>
                        Войти с Яндекс ID
                      </Button>
                    </div>

                    <div className={styles.linksContainer}>
                      <div className={styles.linkRow}>
                        <span>Уже есть учетная запись? </span>
                        <Link to="/login" className={styles.link}>
                          Войти
                        </Link>
                      </div>
                    </div>
                  </Field>
                </FieldGroup>
              </form>
            ) : (
              <form onSubmit={handleCodeSubmit}>
                <FieldGroup className={styles.fieldGroup}>
                  <Field className={styles.field}>
                    <FieldLabel htmlFor="code">Код из письма или SMS</FieldLabel>
                    <Input
                      id="code"
                      name="code"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      placeholder="••••••"
                      maxLength={6}
                      required
                      className={styles.input}
                      disabled={loading}
                    />
                    <CardDescription>6 цифр</CardDescription>
                  </Field>
                  <Field>
                    <Button
                      style={{ fontSize: '14px' }}
                      type="submit"
                      className={styles.submitButton}
                      disabled={loading}
                    >
                      Создать аккаунт <ArrowRight />
                    </Button>
                    <Button
                      variant="outline"
                      type="button"
                      className={styles.submitButton}
                      style={{ fontSize: '14px', marginTop: 8 }}
                      disabled={loading}
                      onClick={handleBackToCredentials}
                    >
                      Назад
                    </Button>
                  </Field>
                  <div className={styles.linksContainer}>
                    <div className={styles.linkRow}>
                      <Link to="/login" className={styles.link}>
                        Войти
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
