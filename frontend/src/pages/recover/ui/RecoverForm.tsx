import { Button } from '../../../shared/ui';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../../shared/ui';
import { useState } from 'react';
import {
  Field,
  FieldGroup,
  FieldLabel,
} from '../../../shared/ui';
import { ArrowLeft } from 'lucide-react';
import { cn } from '../../../shared/lib/utils';
import Input from '../../../shared/ui/Input/Input';
import styles from './RecoverPage.module.css';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api'; // функция для установки нового пароля
import { prepareResetPasswordData } from '../../../shared/utils/validation';

export default function RecoverForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  // Получаем токен из URL (пример: /recover?token=abc123)
  const token = searchParams.get('token');
	console.log(token)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const password = (form.elements.namedItem('password') as HTMLInputElement)
      .value;
    const confirmPassword = (form.elements.namedItem('confirmPassword') as HTMLInputElement)
      .value;

    // Валидации
    if (!token) {
      setError('Ссылка для восстановления недействительна или устарела');
      setLoading(false);
      return;
    }

    if (password.length < 6) {
      setError('Пароль должен содержать минимум 6 символов');
      setLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      setLoading(false);
      return;
    }

    try {
      const payload = prepareResetPasswordData(password, token);
      
      await resetPassword(payload);
      setSuccess(true);
      
    } catch (err: any) {
      // Обработка ошибок
      if (err.message.includes('403') || err.message.includes('Invalid token')) {
        setError('Ссылка для восстановления недействительна или устарела');
      } else if (err.message.includes('400')) {
        setError('Некорректные данные');
      } else if (err.message.includes('500')) {
        setError('Сервер временно недоступен. Попробуйте позже.');
      } else {
        setError(err.message || 'Произошла ошибка при смене пароля');
      }
    } finally {
      setLoading(false);
    }
  };

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
              {success 
                ? 'Пароль успешно изменен! Теперь вы можете войти с новым паролем.'
                : 'Установите свой новый пароль и подтвердите его'}
            </CardDescription>
          </CardHeader>
          <CardContent className={styles.cardContent}>
            {success ? (
              <div className={styles.successMessage}>
                <div className={styles.successIcon}>✓</div>
                <p style={{ textAlign: 'center', marginBottom: '20px' }}>
                  Пароль успешно изменен!
                </p>
                <p style={{ textAlign: 'center', fontSize: '14px', color: '#666' }}>
                  Вы будете перенаправлены на страницу входа через 3 секунды...
                </p>
                <Button
                  style={{ fontSize: '14px', marginTop: '20px' }}
                  type="button"
                  className={styles.submitButton}
                  onClick={() => navigate('/login')}
                >
                  Перейти ко входу сразу
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <FieldGroup className={styles.fieldGroup}>
                  {!token && (
                    <div className={styles.errorMessage}>
                      Ссылка для восстановления недействительна или устарела
                    </div>
                  )}
                  
                  <Field className={styles.field}>
                    <div className={styles.passwordHeader}>
                      <FieldLabel htmlFor="password">Новый пароль</FieldLabel>
                    </div>
                    <Input
                      id="password"
                      name="password"
                      type="password"
                      placeholder="••••••••••••••"
                      required
                      className={styles.input}
                      disabled={loading || !token}
                    />
                    <CardDescription style={{ fontSize: '12px', marginTop: '4px' }}>
                      Длина должна быть не меньше 6 символов
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
                      placeholder="••••••••••••••"
                      required
                      className={styles.input}
                      disabled={loading || !token}
                    />
                  </Field>

                  {error && (
                    <div className={styles.errorMessage}>
                      {error}
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
            )}
          </CardContent>
        </Card>
        <div className={styles.copyright}>&copy; 2026 Профессия</div>
      </div>
    </div>
  );
}