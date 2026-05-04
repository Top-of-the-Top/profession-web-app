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
import { cn } from '@shared/lib/utils';
import styles from './LoginPage.module.css';
import { useState } from 'react';
import { useUserStore } from '@entities/user/model/userStore';
import { loginUser } from '../api';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ZodError } from 'zod';
import { Eye, EyeOff } from 'lucide-react';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  consumeAuthLogoutReason,
  type AuthLogoutReason,
} from '@shared/lib/auth/logoutReason';
import { messageForApiFailure, notifyError } from '@shared/lib/sileo/notify';
import {
  preloadRegisterRoute,
  preloadResetRoute,
  warmAppAfterAuth,
} from '@router/lazyPages';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginFormSchema, type LoginFormValues } from '@shared/utils/formSchemas';
import { startYandexOAuth } from '@shared/lib/auth/yandexOAuth';
import { startVkOAuth } from '@shared/lib/auth/vkOAuth';

function notifyLoginFailure(err: unknown) {
  if (err instanceof Error && err.message === 'Invalid email or phone number') {
    notifyError({
      title: 'Неверный формат контакта',
      description: 'Введите корректный email или номер телефона.',
    });
    return;
  }
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('login', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure('login', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

function getLogoutReasonText(reason: AuthLogoutReason | null): string | null {
  if (reason === 'refresh_token_expired') {
    return 'Сессия истекла: refresh-токен просрочен. Войдите снова.';
  }
  if (reason === 'refresh_token_invalid') {
    return 'Сессия сброшена: refresh-токен невалиден. Войдите снова.';
  }
  if (reason === 'refresh_token_missing') {
    return 'Сессия завершена: refresh-токен отсутствует. Войдите снова.';
  }
  if (reason === 'refresh_token_unavailable') {
    return 'Сеанс завершен: сервер авторизации недоступен. Войдите снова.';
  }
  return null;
}

type LoginLocationState = {
  from?: {
    pathname?: string;
    search?: string;
    hash?: string;
  };
  authReason?: AuthLogoutReason | null;
};

export default function LoginForm({ ...props }: React.ComponentProps<'div'>) {
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LoginLocationState | null;
  const login = useUserStore((s) => s.login);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [logoutReasonText] = useState<string | null>(() => {
    const reason = locationState?.authReason ?? consumeAuthLogoutReason();
    return getLogoutReasonText(reason ?? null);
  });
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: { emailOrPhone: '', password: '' },
  });

  const onSubmit = async ({ emailOrPhone, password }: LoginFormValues) => {
    setLoading(true);
    try {
      const payload = await loginUser({ emailOrPhone, password });
      await login(payload);
      await warmAppAfterAuth();
      const from = locationState?.from;
      const fromPath = from?.pathname
        ? `${from.pathname}${from.search ?? ''}${from.hash ?? ''}`
        : null;
      const redirectTo =
        fromPath && fromPath.startsWith('/app') ? fromPath : '/app';
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err instanceof ZodError) {
        notifyError({
          title: 'некорректный ответ сервера',
          description: 'Обновите страницу или попробуйте позже.',
        });
        return;
      }
      notifyLoginFailure(err);
    } finally {
      setLoading(false);
    }
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

  const handleVkLogin = () => {
    void startVkOAuth().catch((err) => {
      notifyError({
        title: 'не удалось запустить вход через VK',
        description: err instanceof Error ? err.message : 'Проверьте настройки OAuth.',
      });
    });
  };

  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="profession-logo-blue.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>Войти</CardTitle>
            <CardDescription>Введите данные ниже, чтобы войти в систему</CardDescription>
            {logoutReasonText ? (
              <CardDescription className={styles.authNotice}>
                {logoutReasonText}
              </CardDescription>
            ) : null}
          </CardHeader>
          <CardContent className={styles.cardContent}>
            <form onSubmit={handleSubmit(onSubmit)}>
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <FieldLabel htmlFor="email">Почта или номер телефона</FieldLabel>
                  <Input
                    id="email"
                    type="email"
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
                  <div className={styles.passwordInputWrap}>
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="password"
                      placeholder="Пароль"
                      className={styles.input}
                      disabled={loading}
                      {...register('password')}
                    />
                    <button
                      type="button"
                      className={styles.passwordToggle}
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                      disabled={loading}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {errors.password?.message ? (
                    <CardDescription>{errors.password.message}</CardDescription>
                  ) : null}
                </Field>
                <Field>
                  <Button
                    style={{ fontSize: '14px' }}
                    type="submit"
                    className={styles.submitButton}
                    disabled={loading}
                  >
                    Войти
                  </Button>
                  <div className={styles.divider}>
                    <span>или</span>
                  </div>
                  <div className={styles.socialButtons}>
                    <Button
                      variant="outline"
                      type="button"
                      className={cn(styles.socialButton, styles.loginVk)}
                      onClick={handleVkLogin}
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
                      <span>Нет аккаунта? </span>
                      <Link
                        to="/register"
                        className={styles.link}
                        onPointerEnter={preloadRegisterRoute}
                        onFocus={preloadRegisterRoute}
                      >
                        Зарегистрироваться
                      </Link>
                    </div>
                    <div className={styles.linkRow}>
                      <Link
                        to="/reset"
                        className={styles.link}
                        onPointerEnter={preloadResetRoute}
                        onFocus={preloadResetRoute}
                      >
                        Забыли пароль?
                      </Link>
                    </div>
                  </div>
                </Field>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
        <div className={styles.copyright}>&copy; 2026 Профессия</div>
      </div>
    </div>
  );
}
