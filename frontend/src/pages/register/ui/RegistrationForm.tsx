import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import { useState, useContext } from 'react';

import {
  Field,
  FieldGroup,
  FieldLabel,
} from '../../../shared/ui';

import { ArrowRight } from 'lucide-react';
import { cn } from '../../../shared/lib/utils';
import Input from '../../../shared/ui/Input/Input';
import styles from './RegistrationPage.module.css';
import { registerUser } from '../api';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../../../context/AuthContext';

export default function RegistrationForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const authContext = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
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
      setError('Пароли не совпадают');
      setLoading(false);
      return;
    }

    try {
      const tokens = await registerUser({ emailOrPhone, password });
      authContext?.login(tokens);
      navigate('/app', { replace: true });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img
          className={styles.logo}
          src="landing/profession-logo.svg"
          alt=""
        />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>
              Создать аккаунт
            </CardTitle>
            <CardDescription>
              Начните работу с Профессией уже сегодня
            </CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
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
                  />
                </Field>

                <Field className={styles.field}>
                  <div className={styles.passwordHeader}>
                    <FieldLabel htmlFor="password">Пароль</FieldLabel>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Пароль"
                    required
                    className={styles.input}
                  />
                  <CardDescription>
                    Длина должна быть не меньше 6 символов
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
                    placeholder="••••••••••••••"
                    required
                    className={styles.input}
                  />
                  {error && (
                    <CardDescription style={{ color: 'red' }}>
                      {error}
                    </CardDescription>
                  )}
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
          </CardContent>
        </Card>

        <div className={styles.copyright}>
          &copy; 2026 Профессия
        </div>
      </div>
    </div>
  );
}
