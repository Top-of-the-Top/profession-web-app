import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight } from 'lucide-react';
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
  Spinner,
} from '@shared/ui';
import { apiClient } from '@shared/api/interceptor';
import { useUserStore } from '@entities/user/model/userStore';
import { notifyError } from '@shared/lib/sileo/notify';
import { warmAppAfterAuth } from '@router/lazyPages';
import styles from './TeacherRegisterPage.module.css';

type ValidateState =
  | { status: 'loading' }
  | { status: 'ok'; email: string }
  | { status: 'used' }
  | { status: 'expired' }
  | { status: 'not_found' };

export default function TeacherRegisterPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('invite') ?? '';
  const navigate = useNavigate();
  const login = useUserStore((s) => s.login);

  const [validate, setValidate] = useState<ValidateState>({ status: 'loading' });
  const [form, setForm] = useState({ first_name: '', last_name: '', password: '', repeat: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showRepeat, setShowRepeat] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setValidate({ status: 'not_found' });
      return;
    }
    apiClient
      .request<{ email: string }>(`/api/admin-panel/invites/validate/?token=${encodeURIComponent(token)}`)
      .then((data) => setValidate({ status: 'ok', email: data.email }))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('API_ERROR_400')) {
          try {
            const body = JSON.parse(msg.split('API_ERROR_400: ')[1] ?? '{}');
            if (body?.error === 'used') { setValidate({ status: 'used' }); return; }
            if (body?.error === 'expired') { setValidate({ status: 'expired' }); return; }
          } catch { /* ignore */ }
        }
        setValidate({ status: 'not_found' });
      });
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== form.repeat) {
      notifyError({ title: 'Пароли не совпадают' });
      return;
    }
    if (form.password.length < 8) {
      notifyError({ title: 'Пароль должен быть не менее 8 символов' });
      return;
    }
    setSubmitting(true);
    try {
      const data = await apiClient.request<{
        access_token: string;
        access_expires_at: string;
        refresh_token: string;
        refresh_expires_at: string;
        role: string;
      }>('/api/admin-panel/invites/register/', {
        method: 'POST',
        body: JSON.stringify({
          token,
          password: form.password,
          first_name: form.first_name,
          last_name: form.last_name,
        }),
      });
      await login({
        tokens: {
          access_token: data.access_token,
          access_expires_at: data.access_expires_at,
          refresh_token: data.refresh_token,
          refresh_expires_at: data.refresh_expires_at,
        },
        role: data.role as import('@shared/lib/rbac/roles').UserRole,
      });
      await warmAppAfterAuth();
      navigate('/app', { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('API_ERROR_400')) {
        try {
          const body = JSON.parse(msg.split('API_ERROR_400: ')[1] ?? '{}');
          if (body?.password) {
            notifyError({ title: body.password[0] ?? 'Ошибка пароля' });
            return;
          }
          if (body?.detail) {
            notifyError({ title: body.detail });
            return;
          }
        } catch { /* ignore */ }
      }
      notifyError({ title: 'Ошибка регистрации', description: 'Попробуйте позже.' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.wrapper}>
        <img className={styles.logo} src="/profession-logo-blue.svg" alt="" />

        <Card className={styles.card}>
          {validate.status === 'loading' && (
            <>
              <CardHeader className={styles.cardHeader}>
                <CardTitle className={styles.formTitle}>Проверка приглашения</CardTitle>
              </CardHeader>
              <CardContent className={styles.cardContent}>
                <div className={styles.centered}><Spinner size="lg" /></div>
              </CardContent>
            </>
          )}

          {validate.status === 'used' && (
            <>
              <CardHeader className={styles.cardHeader}>
                <CardTitle className={styles.formTitle}>Ссылка использована</CardTitle>
                <CardDescription>Это приглашение уже было принято.</CardDescription>
              </CardHeader>
              <CardContent className={styles.cardContent}>
                <Button className={styles.submitButton} onClick={() => navigate('/login')}>
                  Войти в аккаунт
                </Button>
              </CardContent>
            </>
          )}

          {validate.status === 'expired' && (
            <>
              <CardHeader className={styles.cardHeader}>
                <CardTitle className={styles.formTitle}>Ссылка истекла</CardTitle>
                <CardDescription>Срок действия приглашения истёк. Запросите новое у администратора.</CardDescription>
              </CardHeader>
              <CardContent className={styles.cardContent} />
            </>
          )}

          {validate.status === 'not_found' && (
            <>
              <CardHeader className={styles.cardHeader}>
                <CardTitle className={styles.formTitle}>Приглашение не найдено</CardTitle>
                <CardDescription>Ссылка недействительна или была удалена.</CardDescription>
              </CardHeader>
              <CardContent className={styles.cardContent} />
            </>
          )}

          {validate.status === 'ok' && (
            <>
              <CardHeader className={styles.cardHeader}>
                <CardTitle className={styles.formTitle}>Создать аккаунт</CardTitle>
                <CardDescription>Вы приглашены как преподаватель на&nbsp;{validate.email}</CardDescription>
              </CardHeader>
              <CardContent className={styles.cardContent}>
                <form onSubmit={handleSubmit}>
                  <FieldGroup className={styles.fieldGroup}>
                    <Field className={styles.field}>
                      <FieldLabel htmlFor="first_name">Имя</FieldLabel>
                      <Input
                        id="first_name"
                        type="text"
                        autoComplete="given-name"
                        placeholder="Имя"
                        className={styles.input}
                        disabled={submitting}
                        value={form.first_name}
                        onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))}
                        required
                      />
                    </Field>

                    <Field className={styles.field}>
                      <FieldLabel htmlFor="last_name">Фамилия</FieldLabel>
                      <Input
                        id="last_name"
                        type="text"
                        autoComplete="family-name"
                        placeholder="Фамилия"
                        className={styles.input}
                        disabled={submitting}
                        value={form.last_name}
                        onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))}
                        required
                      />
                    </Field>

                    <Field className={styles.field}>
                      <FieldLabel htmlFor="password">Пароль</FieldLabel>
                      <div className={styles.passwordWrap}>
                        <Input
                          id="password"
                          type={showPassword ? 'text' : 'password'}
                          autoComplete="new-password"
                          placeholder="Не менее 8 символов"
                          className={styles.input}
                          disabled={submitting}
                          value={form.password}
                          onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
                          required
                        />
                        <button
                          type="button"
                          className={styles.eyeBtn}
                          onClick={() => setShowPassword((v) => !v)}
                          disabled={submitting}
                          aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                        >
                          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </Field>

                    <Field className={styles.field}>
                      <FieldLabel htmlFor="repeat">Повторите пароль</FieldLabel>
                      <div className={styles.passwordWrap}>
                        <Input
                          id="repeat"
                          type={showRepeat ? 'text' : 'password'}
                          autoComplete="new-password"
                          placeholder="Повторите пароль"
                          className={styles.input}
                          disabled={submitting}
                          value={form.repeat}
                          onChange={(e) => setForm((p) => ({ ...p, repeat: e.target.value }))}
                          required
                        />
                        <button
                          type="button"
                          className={styles.eyeBtn}
                          onClick={() => setShowRepeat((v) => !v)}
                          disabled={submitting}
                          aria-label={showRepeat ? 'Скрыть пароль' : 'Показать пароль'}
                        >
                          {showRepeat ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                      </div>
                    </Field>

                    <Field>
                      <Button
                        type="submit"
                        className={styles.submitButton}
                        disabled={submitting || !form.first_name.trim() || !form.last_name.trim() || !form.password}
                      >
                        {submitting ? <Spinner size="sm" /> : <>Зарегистрироваться <ArrowRight size={16} /></>}
                      </Button>
                    </Field>
                  </FieldGroup>
                </form>
              </CardContent>
            </>
          )}
        </Card>

        <div className={styles.copyright}>&copy; 2026 Профессия</div>
      </div>
    </div>
  );
}
