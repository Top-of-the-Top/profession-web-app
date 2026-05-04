import {
  Button,
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
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import styles from './RecoverPage.module.css';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { recoverEmailPassword, recoverSetPassword } from '../api';
import { prepareResetPasswordData } from '@shared/utils/validation';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '@shared/lib/sileo/notify';
import { useUserStore } from '@entities/user/model/userStore';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  recoverSetPasswordSchema,
  type RecoverSetPasswordFormValues,
} from '@shared/utils/formSchemas';

function notifyRecoverFailure(
  err: unknown,
  scene: 'recoverEmail' | 'recoverSet',
) {
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure(scene, 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure(scene, parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

export default function RecoverForm({ ...props }: React.ComponentProps<'div'>) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const login = useUserStore((s) => s.login);
  const redirectTimeoutRef = useRef<number | null>(null);
  const token = searchParams.get('token');
  const channelRaw = searchParams.get('channel');
  const channel = channelRaw === 'phone' ? 'phone' : 'email';
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RecoverSetPasswordFormValues>({
    resolver: zodResolver(recoverSetPasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  });

  useEffect(
    () => () => {
      if (redirectTimeoutRef.current) {
        window.clearTimeout(redirectTimeoutRef.current);
      }
    },
    [],
  );

  const onSubmit = async ({
    password,
  }: RecoverSetPasswordFormValues) => {
    if (!token) {
      notifyError({
        title: 'ссылка недействительна',
        description: 'Откройте ссылку из письма или запросите новую на странице сброса пароля.',
      });
      return;
    }

    setLoading(true);
    const payload = prepareResetPasswordData(password, token);

    try {
      const loginPayload =
        channel === 'email'
          ? await recoverEmailPassword(payload)
          : await recoverSetPassword(payload);
      await login(loginPayload);
      setSuccess(true);
      redirectTimeoutRef.current = window.setTimeout(
        () => navigate('/app', { replace: true }),
        1500,
      );
    } catch (err) {
      notifyRecoverFailure(err, channel === 'email' ? 'recoverEmail' : 'recoverSet');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className={styles.loginPage} {...props}>
        <div className={styles.loginWrapper}>
          <img className={styles.logo} src="landing/profession-logo-blue.svg" alt="" />
          <Card className={styles.card}>
            <CardHeader className={styles.cardHeader}>
              <CardTitle className={styles.formTitleOverride}>
                Пароль успешно изменен!
              </CardTitle>
              <CardDescription>
                Сейчас вы будете перенаправлены в приложение
              </CardDescription>
            </CardHeader>
            <CardContent className={styles.cardContent}>
              <div className={styles.successMessage}>
                <div className={styles.successIcon}>
                  <CheckCircle2 size={48} />
                </div>
                <p className={styles.successRedirectText}>
                  Перенаправляем…
                </p>
                <Button
                  type="button"
                  className={`${styles.submitButton} ${styles.actionButtonOffset}`}
                  onClick={() => navigate('/app', { replace: true })}
                >
                  Перейти сейчас
                </Button>
              </div>
            </CardContent>
          </Card>
          <div className={styles.copyright}>&copy; 2026 Профессия</div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="/profession-logo-blue.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle className={styles.formTitleOverride}>
              Установите новый пароль
            </CardTitle>
            <CardDescription>Введите новый пароль для вашего аккаунта</CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            <form onSubmit={handleSubmit(onSubmit)}>
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <div className={styles.passwordHeader}>
                    <FieldLabel htmlFor="password">Новый пароль</FieldLabel>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••••••••"
                    className={styles.input}
                    disabled={loading || !token}
                    {...register('password')}
                  />
                  <CardDescription className={styles.inputHintText}>
                    Должен содержать минимум 8 символов
                  </CardDescription>
                  {errors.password?.message ? (
                    <CardDescription>{errors.password.message}</CardDescription>
                  ) : null}
                </Field>
                <Field className={styles.field}>
                  <div className={styles.passwordHeader}>
                    <FieldLabel htmlFor="confirmPassword">Подтвердите пароль</FieldLabel>
                  </div>
                  <Input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••••••••"
                    className={styles.input}
                    disabled={loading || !token}
                    {...register('confirmPassword')}
                  />
                  {errors.confirmPassword?.message ? (
                    <CardDescription>{errors.confirmPassword.message}</CardDescription>
                  ) : null}
                </Field>
                {!token && (
                  <div className={styles.tokenError}>
                    <p>Ссылка для восстановления недействительна или отсутствует</p>
                    <Link to="/reset" className={styles.link}>
                      Запросить новую ссылку
                    </Link>
                  </div>
                )}
                <Button
                  type="submit"
                  className={styles.submitButton}
                  disabled={loading || !token}
                >
                  {loading ? 'Смена пароля...' : 'Установить новый пароль'}
                </Button>
                <div className={styles.linksContainer}>
                  <div className={styles.linkRow}>
                    <Link to="/login" className={styles.link}>
                      <ArrowLeft size={20} /> Вернуться ко входу
                    </Link>
                  </div>
                </div>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
        <div className={styles.copyright}>&copy; 2026 Профессия</div>
      </div>
    </div>
  );
}
