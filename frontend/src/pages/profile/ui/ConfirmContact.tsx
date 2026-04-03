import { useState, useEffect, type ChangeEvent } from 'react';
import { Button, Input, Label } from '../../../shared/ui';
import { X, AlertCircle } from 'lucide-react';
import styles from './ConfirmContact.module.css';
import { cn } from '../../../shared/lib/utils';

type FormStep = 'input' | 'code';

interface ConfirmContactProps {
  type: 'email' | 'phone';
  isVisible: boolean;
  onClose?: () => void;
  /** PATCH профиля с новым контактом; после успеха показывается шаг ввода кода. */
  onRequestChange: (contact: string) => Promise<void>;
  /** Подтверждение кода из письма или SMS. */
  onVerify: (code: string) => Promise<void>;
}

export default function ConfirmContact({
  type,
  isVisible,
  onClose,
  onRequestChange,
  onVerify,
}: ConfirmContactProps) {
  const [step, setStep] = useState<FormStep>('input');
  const [contact, setContact] = useState<string>('');
  const [code, setCode] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isVisible) {
      setStep('input');
      setContact('');
      setCode('');
      setError('');
      setIsLoading(false);
    }
  }, [isVisible]);

  const title =
    type === 'email' ? 'Подтверждение почты' : 'Подтверждение номера';

  const descriptions = {
    input: `Введите ${type === 'email' ? 'новый адрес почты' : 'новый номер телефона'}`,
    code: `Введите 6 цифр из ${type === 'email' ? 'письма' : 'SMS'}`,
  };

  const handleContinue = async (): Promise<void> => {
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
      if (digits.length !== 10 && digits.length !== 11) {
        setError('Введите корректный номер телефона');
        return;
      }
    }

    setError('');
    setIsLoading(true);
    try {
      await onRequestChange(type === 'email' ? contact.trim() : contact);
      setStep('code');
    } catch {
      /* тосты об ошибке — в родителе */
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmCode = async (): Promise<void> => {
    if (code.length !== 6) {
      setError('Введите 6 цифр кода');
      return;
    }

    setError('');
    setIsLoading(true);
    try {
      await onVerify(code);
    } catch {
      /* тосты — в родителе */
    } finally {
      setIsLoading(false);
    }
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
      const digits = raw.replace(/\D/g, '').slice(0, 11);
      setContact(digits);
      return;
    }

    setContact(raw);
    if (error) setError('');
  };

  const handleCodeChange = (e: ChangeEvent<HTMLInputElement>): void => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
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
            onClick={() => void handleContinue()}
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
              placeholder="••••••"
              maxLength={6}
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
              onClick={() => void handleConfirmCode()}
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
