import { Button } from '@shared/ui';
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
} from '@shared/ui';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@shared/lib/utils';
import styles from './RegistrationPage.module.css';
import { completeRegisterWithCode, requestRegisterCode } from '../api';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useUserStore } from '@entities/user/model/userStore';
import { ZodError } from 'zod';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError, notifySuccess } from '@shared/lib/sileo/notify';
import { validateEmailOrPhone } from '@shared/utils/validation';
import { OtpInput, EMPTY_OTP, type OtpValue } from '@components/OtpInput';
import { preloadLoginRoute } from '@router/lazyPages';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  registerCredentialsSchema,
  type RegisterCredentialsFormValues,
} from '@shared/utils/formSchemas';
import { startYandexOAuth } from '@shared/lib/auth/yandexOAuth';

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
  const [otp, setOtp] = useState<OtpValue>(() => [...EMPTY_OTP]);

  const login = useUserStore((s) => s.login);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const verifyInFlightRef = useRef(false);
  const verifySucceededRef = useRef(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterCredentialsFormValues>({
    resolver: zodResolver(registerCredentialsSchema),
    defaultValues: { emailOrPhone: '', password: '', repeatPassword: '' },
  });

  useLayoutEffect(() => {
    if (!import.meta.env.DEV || searchParams.get('debug') !== 'code') return;
    const kind = searchParams.get('kind') === 'phone' ? 'phone' : 'email';
    const raw = searchParams.get('contact')?.trim();
    const contact =
      raw && raw.length > 0
        ? raw
        : kind === 'email'
          ? 'dev@example.com'
          : '+79000000000';
    verifySucceededRef.current = false;
    setPendingKind(kind);
    setPendingContact(contact);
    setCodeSentDetail('Отладка: шаг ввода кода');
    setOtp([...EMPTY_OTP]);
    setStep('code');
  }, [searchParams]);

  const submitVerificationCode = useCallback(
    async (code: string) => {
      if (!pendingKind || !pendingContact) return;
      if (verifyInFlightRef.current || verifySucceededRef.current) return;
      verifyInFlightRef.current = true;
      setLoading(true);
      try {
        const loginPayload = await completeRegisterWithCode({
          kind: pendingKind,
          normalizedContact: pendingContact,
          code,
        });
        await login(loginPayload);
        verifySucceededRef.current = true;
        setOtp([...EMPTY_OTP]);
        navigate('/app', { replace: true });
      } catch (err) {
        if (verifySucceededRef.current) return;
        if (err instanceof ZodError) {
          notifyError({
            title: 'некорректный ответ сервера',
            description: formatZodRegisterError(err),
          });
        } else {
          notifyRegisterVerifyFailure(err);
        }
        setOtp([...EMPTY_OTP]);
      } finally {
        setLoading(false);
        verifyInFlightRef.current = false;
      }
    },
    [pendingKind, pendingContact, login, navigate],
  );

  useEffect(() => {
    if (step !== 'code' || loading || verifySucceededRef.current) return;
    const code = otp.join('');
    const complete = otp.every((cell: string) => cell !== '') && code.length === 6;
    if (!complete) return;
    void submitVerificationCode(code);
  }, [otp, step, loading, submitVerificationCode]);

  const handleCredentialsSubmit = async ({
    emailOrPhone,
    password,
  }: RegisterCredentialsFormValues) => {
    setLoading(true);

    const validation = validateEmailOrPhone(emailOrPhone);

    try {
      const res = await requestRegisterCode({ emailOrPhone, password });
      if (res.flow === 'immediate') {
        notifySuccess({
          title: 'аккаунт создан',
          description: 'Сейчас выполняется вход…',
        });
        await login(res.loginPayload);
        navigate('/app', { replace: true });
        return;
      }
      setCodeSentDetail(res.detail);
      setPendingKind(validation.isEmail ? 'email' : 'phone');
      setPendingContact(validation.normalized);
      verifySucceededRef.current = false;
      setOtp([...EMPTY_OTP]);
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

  const handleBackToCredentials = () => {
    verifySucceededRef.current = false;
    setStep('credentials');
    setPendingKind(null);
    setPendingContact(null);
    setCodeSentDetail(null);
    setOtp([...EMPTY_OTP]);
  };

  const handleYandexLogin = () => {
    try {
      startYandexOAuth();
    } catch (err) {
      notifyError({
        title: 'не удалось запустить вход через Яндекс',
        description: err instanceof Error ? err.message : 'Проверьте настройки OAuth.',
      });
    }
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
              <form onSubmit={handleSubmit(handleCredentialsSubmit)}>
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
                      className={styles.input}
                      disabled={loading}
                      {...register('emailOrPhone')}
                    />
                    {errors.emailOrPhone?.message ? (
                      <CardDescription>{errors.emailOrPhone.message}</CardDescription>
                    ) : null}
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
                      className={styles.input}
                      disabled={loading}
                      {...register('password')}
                    />
                    <CardDescription>
                      Не меньше 8 символов
                    </CardDescription>
                    {errors.password?.message ? (
                      <CardDescription>{errors.password.message}</CardDescription>
                    ) : null}
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
                      className={styles.input}
                      disabled={loading}
                      {...register('repeatPassword')}
                    />
                    {errors.repeatPassword?.message ? (
                      <CardDescription>{errors.repeatPassword.message}</CardDescription>
                    ) : null}
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
                        onClick={handleYandexLogin}
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
                        <Link
                          to="/login"
                          className={styles.link}
                          onPointerEnter={preloadLoginRoute}
                          onFocus={preloadLoginRoute}
                        >
                          Войти
                        </Link>
                      </div>
                    </div>
                  </Field>
                </FieldGroup>
              </form>
            ) : (
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <FieldLabel>Код из письма или SMS</FieldLabel>
                  <OtpInput value={otp} onChange={setOtp} disabled={loading} />
                  <p className={styles.otpHint}>
                    После ввода всех 6 цифр подтверждение отправится автоматически
                  </p>
                </Field>
                <Field>
                  <Button
                    type="button"
                    variant="outline"
                    className={styles.backButton}
                    disabled={loading}
                    onClick={handleBackToCredentials}
                  >
                    Назад
                  </Button>
                </Field>
                
              </FieldGroup>
            )}
          </CardContent>
        </Card>

        <div className={styles.copyright}>&copy; 2026 Профессия</div>
      </div>
    </div>
  );
}
