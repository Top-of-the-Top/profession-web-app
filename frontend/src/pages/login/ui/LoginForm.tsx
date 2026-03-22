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
import { cn } from '../../../shared/lib/utils';
import styles from './LoginPage.module.css';
import { useContext, useState } from 'react';
import { AuthContext } from '../../../context/AuthContext';
import { loginUser } from '../api';
import { Link, useNavigate } from 'react-router-dom';
import { ZodError } from 'zod';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '../../../shared/lib/sileo/notify';

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
  const authContext = useContext(AuthContext);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const form = e.currentTarget as HTMLFormElement;
    const emailOrPhone = (form.elements.namedItem('email') as HTMLInputElement).value;
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;
    try {
      const tokens = await loginUser({ emailOrPhone, password });
      authContext?.login(tokens);
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
        <img className={styles.logo} src="profession-logo.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>Войти</CardTitle>
            <CardDescription>Введите данные ниже, чтобы войти в систему</CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            <form onSubmit={handleSubmit}>
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <FieldLabel htmlFor="email">Почта или номер телефона</FieldLabel>
                  <Input
                    id="email"
                    type="text"
                    autoComplete="email"
                    placeholder="Почта/телефон"
                    required
                    className={styles.input}
                  />
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
                    required
                    className={styles.input}
                  />
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
                      <Link to="/register" className={styles.link}>
                        Зарегистрироваться
                      </Link>
                    </div>
                    <div className={styles.linkRow}>
                      <Link to="/reset" className={styles.link}>
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
