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
import { cn } from '@shared/lib/utils';
import styles from './LoginPage.module.css';
import { useState } from 'react';
import { useUserStore } from '@entities/user/model/userStore';
import { loginUser } from '../api';
import { Link, useNavigate } from 'react-router-dom';
import { ZodError } from 'zod';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '@shared/lib/sileo/notify';
import { preloadRegisterRoute, preloadResetRoute } from '@router/lazyPages';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { loginFormSchema, type LoginFormValues } from '@shared/utils/formSchemas';

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

export default function LoginForm({ ...props }: React.ComponentProps<'div'>) {
  const navigate = useNavigate();
  const login = useUserStore((s) => s.login);
  const [loading, setLoading] = useState(false);
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
      navigate('/app', { replace: true });
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

  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="profession-logo-blue.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>Войти</CardTitle>
            <CardDescription>Введите данные ниже, чтобы войти в систему</CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            <form onSubmit={handleSubmit(onSubmit)}>
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <FieldLabel htmlFor="email">Почта или номер телефона</FieldLabel>
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
                    autoComplete="password"
                    placeholder="Пароль"
                    className={styles.input}
                    disabled={loading}
                    {...register('password')}
                  />
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
