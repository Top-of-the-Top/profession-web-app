import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import {
  Field,
  // FieldDescription,
  FieldGroup,
  FieldLabel,
} from '../../../shared/ui';

import { ArrowLeft } from 'lucide-react';
import { cn } from '../../../shared/lib/utils';
import Input from '../../../shared/ui/Input/Input';
import styles from './ResetPage.module.css';

export default function ResetForm({
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
              Сброс пароля
            </CardTitle>
            <CardDescription>
              Введите свой адрес электронной почты или номер телефона, и мы
              вышлем вам ссылку для сброса вашего пароля
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
               <Button
                    style={{ fontSize: '14px' }}
                    type="submit"
                    className={styles.submitButton}
                  >
                    Отправить код
                  </Button>
                <div className={styles.linksContainer}>
                    <div className={styles.linkRow}>
                      <a href="#" className={styles.link}>
                        <ArrowLeft size={20} /> Обратно ко входу
                      </a>
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
