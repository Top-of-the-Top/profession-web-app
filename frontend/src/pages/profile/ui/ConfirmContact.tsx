import { useState, useEffect } from 'react';
import { Button, Input, Label } from '@shared/ui';
import { X, AlertCircle } from 'lucide-react';
import styles from './ConfirmContact.module.css';
import { cn } from '@shared/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  confirmContactCodeSchema,
  confirmEmailContactSchema,
  confirmPhoneContactSchema,
  type ConfirmContactCodeFormValues,
  type ConfirmContactInputFormValues,
} from '@shared/utils/formSchemas';

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
  const [isLoading, setIsLoading] = useState(false);
  const inputSchema =
    type === 'email' ? confirmEmailContactSchema : confirmPhoneContactSchema;
  const {
    register: registerInput,
    handleSubmit: handleInputSubmit,
    reset: resetInput,
    setError: setInputError,
    clearErrors: clearInputErrors,
    watch: watchInput,
    formState: { errors: inputErrors },
  } = useForm<ConfirmContactInputFormValues>({
    resolver: zodResolver(inputSchema),
    defaultValues: { contact: '' },
  });
  const {
    register: registerCode,
    handleSubmit: handleCodeSubmit,
    reset: resetCode,
    clearErrors: clearCodeErrors,
    formState: { errors: codeErrors },
  } = useForm<ConfirmContactCodeFormValues>({
    resolver: zodResolver(confirmContactCodeSchema),
    defaultValues: { code: '' },
  });
  const contactField = registerInput('contact');
  const codeField = registerCode('code');
  const contact = watchInput('contact');

  useEffect(() => {
    if (!isVisible) {
      setStep('input');
      resetInput({ contact: '' });
      resetCode({ code: '' });
      setIsLoading(false);
    }
  }, [isVisible, resetCode, resetInput]);

  const title =
    type === 'email' ? 'Подтверждение почты' : 'Подтверждение номера';

  const descriptions = {
    input: `Введите ${type === 'email' ? 'новый адрес почты' : 'новый номер телефона'}`,
    code: `Введите 6 цифр из ${type === 'email' ? 'письма' : 'SMS'}`,
  };

  const handleContinue = async ({
    contact,
  }: ConfirmContactInputFormValues): Promise<void> => {
    setIsLoading(true);
    try {
      await onRequestChange(type === 'email' ? contact.trim() : contact);
      setStep('code');
    } catch {
      setInputError('contact', { message: 'Не удалось отправить код подтверждения' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmCode = async ({
    code,
  }: ConfirmContactCodeFormValues): Promise<void> => {
    setIsLoading(true);
    try {
      await onVerify(code);
    } catch {
      return;
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = (): void => {
    setStep('input');
    resetInput({ contact: '' });
    resetCode({ code: '' });
    setIsLoading(false);
    onClose?.();
  };

  const handleBack = (): void => {
    setStep('input');
    resetCode({ code: '' });
    clearCodeErrors();
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
        <form className={styles.form} onSubmit={handleInputSubmit(handleContinue)}>
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
              name={contactField.name}
              ref={contactField.ref}
              onBlur={contactField.onBlur}
              onChange={(e) => {
                if (type === 'phone') {
                  e.target.value = e.target.value.replace(/\D/g, '').slice(0, 11);
                }
                contactField.onChange(e);
                clearInputErrors('contact');
              }}
              className={cn(styles.input, inputErrors.contact && styles.inputError)}
              placeholder={
                type === 'email' ? 'example@mail.ru' : '+7 (xxx) xxx-xx-xx'
              }
              disabled={isLoading}
            />
            {inputErrors.contact?.message && (
              <div className={styles.errorText}>
                <AlertCircle className="h-4 w-4" />
                {inputErrors.contact.message}
              </div>
            )}
          </div>

          <Button
            className={styles.saveButton}
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? 'Отправка...' : 'Продолжить'}
          </Button>
        </form>
      )}

      {step === 'code' && (
        <form className={styles.form} onSubmit={handleCodeSubmit(handleConfirmCode)}>
          <div className={styles.formGroup}>
            <Label htmlFor="code" className={styles.label}>
              Введите код
            </Label>
            <Input
              id="code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              name={codeField.name}
              ref={codeField.ref}
              onBlur={codeField.onBlur}
              onChange={(e) => {
                e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
                codeField.onChange(e);
                clearCodeErrors('code');
              }}
              className={cn(styles.input, codeErrors.code && styles.inputError)}
              placeholder="••••••"
              maxLength={6}
              disabled={isLoading}
            />
            {codeErrors.code?.message && (
              <div className={styles.errorText}>
                <AlertCircle className="h-4 w-4" />
                {codeErrors.code.message}
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
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? 'Проверка...' : 'Подтвердить'}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
