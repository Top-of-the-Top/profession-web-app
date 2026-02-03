import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui/';
import {
  Field,
  // FieldDescription,
  FieldGroup,
  FieldLabel,
} from '../../../shared/ui';
import { cn } from '../../../shared/lib/utils';
import Input from '../../../shared/ui/Input/Input';
import styles from './LoginPage.module.css';
import { useContext, useState } from 'react';
import { AuthContext } from '../../../context/AuthContext';
import { loginUser } from '../api';
import { Link } from 'react-router-dom';

export default function LoginForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const authContext = useContext(AuthContext);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const emailOrPhone = (form.elements.namedItem('email') as HTMLInputElement)
      .value;
    const password = (form.elements.namedItem('password') as HTMLInputElement)
      .value;
		// console.log(emailOrPhone + '   ' + password)
    try {
      const tokens = await loginUser({ emailOrPhone, password });
      authContext?.login(tokens);
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
                Войти
              </CardTitle>
              <CardDescription>
                Введите данные ниже, чтобы войти в систему
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
                        <Link to='/register' className={styles.link}>
                          Зарегистрироваться
                        </Link>
                      </div>
                      <div className={styles.linkRow}>
                        <Link to='/reset' className={styles.link}>
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
