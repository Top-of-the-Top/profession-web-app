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
import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import Input from '../../../shared/ui/Input/Input';
import styles from './RecoverPage.module.css';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api';
import { prepareResetPasswordData } from '../../../shared/utils/validation';
import toast, { Toaster } from 'react-hot-toast';

export default function RecoverForm({
  className,
  ...props
}: React.ComponentProps<'div'>) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  // Получаем токен из URL
  const token = searchParams.get('token');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget as HTMLFormElement;
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;
    const confirmPassword = (form.elements.namedItem('confirmPassword') as HTMLInputElement).value;

    // Базовые валидации
    if (!token) {
      toast.error('Ссылка для восстановления недействительна');
      setLoading(false);
      return;
    }

    if (password.length < 6) {
      toast.error('Пароль должен содержать минимум 6 символов');
      setLoading(false);
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Пароли не совпадают');
      setLoading(false);
      return;
    }

    try {
      const payload = prepareResetPasswordData(password, token);
      
      await resetPassword(payload);
      
      toast.success('Пароль успешно изменен! Теперь вы можете войти с новым паролем.', {
        duration: 5000,
        icon: <CheckCircle2 className={styles.toastSuccessIcon} />,
      });
      
      setSuccess(true);
      
      // Перенаправляем на страницу входа через 3 секунды
      setTimeout(() => {
        navigate('/login');
      }, 3000);
      
    } catch (err: any) {
      // Обработка различных ошибок сервера
      if (err.response?.status === 400) {
        toast.error('Некорректные данные для смены пароля');
      } else if (err.response?.status === 403) {
        toast.error('Действие ссылки истекло. Запросите новую ссылку для восстановления');
      } else if (err.response?.status === 404) {
        toast.error('Ссылка для восстановления не найдена или устарела');
      } else if (err.response?.status === 410) {
        toast.error('Время действия ссылки истекло. Запросите новую ссылку');
      } else if (err.response?.status === 429) {
        toast.error('Слишком много попыток. Попробуйте позже');
      } else if (err.response?.status === 500) {
        toast.error('Сервер временно недоступен. Попробуйте позже');
      } else {
        toast.error(err.message || 'Произошла ошибка при смене пароля');
      }
    } finally {
      setLoading(false);
    }
  };

  // Если пароль успешно изменен
  if (success) {
    return (
      <div className={styles.loginPage} {...props}>
        <div className={styles.loginWrapper}>
          <img className={styles.logo} src="landing/profession-logo.svg" alt="" />
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
        <Toaster 
          position="top-center"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
              borderRadius: '8px',
              fontSize: '14px',
            },
            success: {
              duration: 5000,
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
          }}
        />
      </div>
    );
  }

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
              Введите новый пароль для вашего аккаунта
            </CardDescription>
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
                    <Link to="/forgot-password" className={styles.link}>
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
      
      <Toaster 
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
            borderRadius: '8px',
            fontSize: '14px',
          },
          success: {
            duration: 5000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  );
}