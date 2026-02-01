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

export default function LoginForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  return (
    <div className={styles.loginPage} {...props}>
      <div className={styles.loginWrapper}>
        <img className={styles.logo} src="landing/profession-logo.svg" alt="" />
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
            <form>
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <FieldLabel htmlFor="email">
                    Почта или номер телефона
                  </FieldLabel>
                  <Input
                    id="email"
                    type="text"
                    placeholder="abrakadabra@yandex.ru"
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
                    placeholder="••••••••••••••"
                    required
                    className={styles.input}
                  />
                </Field>
                <Field>
                  <Button
                    style={{ fontSize: '14px' }}
                    type="submit"
                    className={styles.submitButton}
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
                      <a href="#" className={styles.link}>
                        Зарегистрироваться
                      </a>
                    </div>
                    <div className={styles.linkRow}>
                      <a href="#" className={styles.link}>
                        Забыли пароль?
                      </a>
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
