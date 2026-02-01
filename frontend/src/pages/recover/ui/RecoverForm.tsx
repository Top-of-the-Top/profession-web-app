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
import styles from './RecoverPage.module.css';

export default function RecoverForm({
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
              Установите новый пароль
            </CardTitle>
            <CardDescription>
              Установите свой новый пароль и подтвердите его
            </CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            <form>
              <FieldGroup className={styles.fieldGroup}>
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
								<Field className={styles.field}>
                  <div className={styles.passwordHeader}>
                    <FieldLabel htmlFor="password">Подтвердите пароль</FieldLabel>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••••••••"
                    required
                    className={styles.input}
                  />
                </Field>
               <Button
                    style={{ fontSize: '14px' }}
                    type="submit"
                    className={styles.submitButton}
                  >
                    Установить новый пароль
                  </Button>
                <div className={styles.linksContainer}>
                    <div className={styles.linkRow}>
                      <a href="#" className={styles.link}>
                        <ArrowLeft size={20} /> Вернуться ко входу
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
