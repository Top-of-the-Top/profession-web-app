import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import { useState } from 'react';
import { Field, FieldGroup, FieldLabel, Input } from '../../../shared/ui';
import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import styles from './RecoverPage.module.css';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api';
import { prepareResetPasswordData } from '../../../shared/utils/validation';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '../../../shared/lib/sileo/notify';

const RECOVER_CHECKS: Array<{
  when: (ctx: { token: string | null; password: string; confirm: string }) => boolean;
  title: string;
  description: string;
}> = [
  {
    when: ({ token }) => !token,
    title: 'ссылка недействительна',
    description: 'Откройте ссылку из письма или запросите новую на странице сброса пароля.',
  },
  {
    when: ({ password }) => password.length < 6,
    title: 'короткий пароль',
    description: 'Пароль должен быть не короче 6 символов.',
  },
  {
    when: ({ password, confirm }) => password !== confirm,
    title: 'пароли не совпадают',
    description: 'Введите одинаковый пароль в оба поля.',
  },
];

function notifyRecoverFailure(err: unknown) {
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('recoverSet', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure('recoverSet', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

export default function RecoverForm({ ...props }: React.ComponentProps<'div'>) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;
    const confirmPassword = (form.elements.namedItem('confirmPassword') as HTMLInputElement).value;

    const ctx = { token, password, confirm: confirmPassword };
    const failed = RECOVER_CHECKS.find((c) => c.when(ctx));
    if (failed) {
      notifyError({ title: failed.title, description: failed.description });
      setLoading(false);
      return;
    }

    try {
      await resetPassword(prepareResetPasswordData(password, token!));
      setSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      notifyRecoverFailure(err);
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
              <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>
                Пароль успешно изменен!
              </CardTitle>
              <CardDescription>
                Теперь вы можете войти в свой аккаунт с новым паролем
              </CardDescription>
            </CardHeader>
            <CardContent className={styles.cardContent}>
              <div className={styles.successMessage}>
                <div className={styles.successIcon}>
                  <CheckCircle2 size={48} />
                </div>
                <p style={{ textAlign: 'center', marginBottom: '20px' }}>
                  Перенаправляем на страницу входа...
                </p>
                <Button
                  style={{ fontSize: '14px', marginTop: '20px' }}
                  type="button"
                  className={styles.submitButton}
                  onClick={() => navigate('/login')}
                >
                  Перейти ко входу сейчас
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
        <img className={styles.logo} src="landing/profession-logo-blue.svg" alt="" />
        <Card className={styles.card}>
          <CardHeader className={styles.cardHeader}>
            <CardTitle style={{ fontSize: '23px', fontWeight: 800 }}>
              Установите новый пароль
            </CardTitle>
            <CardDescription>Введите новый пароль для вашего аккаунта</CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            <form onSubmit={handleSubmit}>
              <FieldGroup className={styles.fieldGroup}>
                <Field className={styles.field}>
                  <div className={styles.passwordHeader}>
                    <FieldLabel htmlFor="password">Новый пароль</FieldLabel>
                  </div>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••••••••"
                    required
                    className={styles.input}
                    disabled={loading || !token}
                  />
                  <CardDescription style={{ fontSize: '12px', marginTop: '4px' }}>
                    Должен содержать минимум 6 символов
                  </CardDescription>
                </Field>
                <Field className={styles.field}>
                  <div className={styles.passwordHeader}>
                    <FieldLabel htmlFor="confirmPassword">Подтвердите пароль</FieldLabel>
                  </div>
                  <Input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    placeholder="••••••••••••••"
                    required
                    className={styles.input}
                    disabled={loading || !token}
                  />
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
                  style={{ fontSize: '14px' }}
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
