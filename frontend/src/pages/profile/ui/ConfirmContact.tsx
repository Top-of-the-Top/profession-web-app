import { useState, type ChangeEvent } from 'react';
import { Button, Input, Label } from '../../../shared/ui';
import { X, CheckCircle2, AlertCircle } from 'lucide-react';
import styles from './ConfirmContact.module.css';
import { cn } from '../../../shared/lib/utils';

type FormStep = 'input' | 'code' | 'success';

interface ConfirmContactProps {
  type: 'email' | 'phone';
  isVisible: boolean;
  onClose?: () => void;
  onSave?: ({ contact, code }: { contact: string; code?: string }) => void;
}

export default function ConfirmContact({
  type,
  isVisible,
  onClose,
  onSave,
}: ConfirmContactProps) {
  const [step, setStep] = useState<FormStep>('input');
  const [contact, setContact] = useState<string>('');
  const [code, setCode] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const title =
    type === 'email' ? 'Подтверждение почты' : 'Подтверждение номера';

  const descriptions = {
    input: `Введите ${type === 'email' ? 'свой адрес почты' : 'свой номер телефона'} для подтверждения`,
		code: `Введите код, который мы отправили Вам, чтобы подтвердить ${type === 'email' ? 'адрес почты' : 'номер телефона'}`,
    success:
      type === 'email'
        ? 'Почта успешно подтверждена'
        : 'Номер успешно подтвержден',
  };

  const handleContinue = (): void => {
    if (!contact.trim()) {
      setError(`Введите ${type === 'email' ? 'почту' : 'номер телефона'}`);
      return;
    }

    if (type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) {
      setError('Введите корректный адрес почты');
      return;
    }

    if (type === 'phone') {
      const digits = contact.replace(/\D/g, '');
      // Валидация проекта: допустимы только 10 или 11 цифр телефона
      if (digits.length !== 10 && digits.length !== 11) {
      setError('Введите корректный номер телефона');
      return;
      }
    }

    setError('');
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      setStep('code');
      onSave?.({ contact });
    }, 500);
  };

  const handleConfirmCode = (): void => {
    if (code.length < 4) {
      setError('Код должен содержать не менее 4 символов');
      return;
    }

    setError('');
    setIsLoading(true);

    setTimeout(() => {
      handleClose();
    }, 500);
  };

  const handleClose = (): void => {
    setStep('input');
    setContact('');
    setCode('');
    setError('');
    setIsLoading(false);
    onClose?.();
  };

  const handleBack = (): void => {
    setStep('input');
    setCode('');
    setError('');
  };

  const handleContactChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const raw = e.target.value;

    if (type === 'phone') {
      // Для телефона разрешаем только цифры и ограничиваем длину по кол-ву цифр.
      const digits = raw.replace(/\D/g, '').slice(0, 11);
      setContact(digits);
      return;
    }

    setContact(raw);
    if (error) setError('');
  };

  const handleCodeChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const value = e.target.value.replace(/\D/g, '');
    setCode(value);
    if (error) setError('');
  };

  if (!isVisible) return null;

  return (
    <div className={styles.container}>
      <div className={styles.titleHeader}>
        <h2 className={styles.title}>{title}</h2>
        <button
          className={styles.closeButton}
          onClick={handleClose}
          type="button"
          aria-label="Закрыть"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <p className={styles.description}>{descriptions[step]}</p>

      {step === 'input' && (
        <div className={styles.form}>
          <div className={styles.formGroup}>
            <Label htmlFor="contact" className={styles.label}>
              {type === 'email' ? 'Адрес почты' : 'Номер телефона'}
            </Label>
            <Input
              id="contact"
              value={contact}
              type={type === 'email' ? 'email' : 'tel'}
              inputMode={type === 'email' ? 'email' : 'numeric'}
              pattern={type === 'email' ? undefined : '[0-9]*'}
              // Для формата "+7..." нужен лимит на 1 символ больше из-за "+"
              maxLength={type === 'email' ? undefined : 12}
              onChange={handleContactChange}
              className={cn(styles.input, error && styles.inputError)}
              placeholder={
                type === 'email' ? 'example@mail.ru' : '+7 (xxx) xxx-xx-xx'
              }
              disabled={isLoading}
            />
            {error && (
              <div className={styles.errorText}>
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}
          </div>

          <Button
            className={styles.saveButton}
            onClick={handleContinue}
            type="button"
            disabled={isLoading}
          >
            {isLoading ? 'Отправка...' : 'Продолжить'}
          </Button>
        </div>
      )}

      {step === 'code' && (
        <div className={styles.form}>
          <div className={styles.formGroup}>
            <Label htmlFor="code" className={styles.label}>
              Введите код
            </Label>
            <Input
              id="code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={code}
              onChange={handleCodeChange}
              className={cn(styles.input, error && styles.inputError)}
              placeholder="••••••••"
              maxLength={8}
              disabled={isLoading}
            />
            {error && (
              <div className={styles.errorText}>
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}
          </div>

          <div className={styles.buttonGroup}>
            <Button
              variant="outline"
              className={styles.backButton}
              onClick={handleBack}
              type="button"
              disabled={isLoading}
            >
              Назад
            </Button>
            <Button
              className={styles.saveButton}
              onClick={handleConfirmCode}
              type="button"
              disabled={isLoading}
            >
              {isLoading ? 'Проверка...' : 'Подтвердить'}
            </Button>
          </div>
        </div>
      )}

    </div>
  );
}
